package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"github.com/skip2/go-qrcode"
	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/binary/proto"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
)

var waClient *whatsmeow.Client

func envOrDefault(name string, fallback string) string {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	return value
}

func waEventHandler(evt interface{}) {
	switch v := evt.(type) {
	case *events.Message:
		if v.Info.IsFromMe {
			return
		}

		text := v.Message.GetConversation()
		if text == "" && v.Message.ExtendedTextMessage != nil {
			text = v.Message.ExtendedTextMessage.GetText()
		}
		if text == "" {
			return
		}

		payload := map[string]interface{}{
			"event":    "MESSAGES_UPSERT",
			"instance": envOrDefault("WHATSAPP_INSTANCE", "personal-assistant"),
			"data": map[string]interface{}{
				"key": map[string]interface{}{
					"remoteJid": v.Info.Chat.String(),
					"fromMe":    false,
					"id":        v.Info.ID,
				},
				"message": map[string]interface{}{
					"conversation": text,
				},
				"pushName": v.Info.PushName,
			},
		}

		if v.Message.ExtendedTextMessage != nil && v.Message.ExtendedTextMessage.ContextInfo != nil {
			ctx := v.Message.ExtendedTextMessage.ContextInfo
			if ctx.StanzaID != nil {
				payload["data"].(map[string]interface{})["message"] = map[string]interface{}{
					"extendedTextMessage": map[string]interface{}{
						"text": text,
						"contextInfo": map[string]interface{}{
							"stanzaId": *ctx.StanzaID,
							"quotedMessage": map[string]interface{}{
								"conversation": "",
							},
						},
					},
				}
			}
		}

		jsonData, err := json.Marshal(payload)
		if err != nil {
			fmt.Printf("[Gateway] Failed to encode webhook payload: %v\n", err)
			return
		}

		webhookURL := envOrDefault("PYTHON_WEBHOOK_URL", "http://localhost:8000/webhook/whatsmeow")
		req, err := http.NewRequest("POST", webhookURL, bytes.NewBuffer(jsonData))
		if err != nil {
			fmt.Printf("[Gateway] Failed to create webhook request: %v\n", err)
			return
		}

		req.Header.Set("Content-Type", "application/json")
		webhookSecret := os.Getenv("WEBHOOK_SECRET")
		if webhookSecret != "" {
			req.Header.Set("Authorization", "Bearer "+webhookSecret)
		}

		client := &http.Client{Timeout: 10 * time.Second}
		go func() {
			resp, err := client.Do(req)
			if err != nil {
				fmt.Printf("[Gateway] Failed to deliver webhook: %v\n", err)
				return
			}
			resp.Body.Close()
		}()
	}
}

func sendHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Metodo nao permitido", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Number string `json:"number"`
		Text   string `json:"text"`
		Quoted string `json:"quoted_id"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	var targetJID types.JID

	if strings.HasSuffix(req.Number, "@lid") {
		user := strings.TrimSuffix(req.Number, "@lid")
		targetJID = types.NewJID(user, "lid")
		fmt.Println("[Gateway] Destino LID detectado.")
	} else if strings.HasSuffix(req.Number, "@s.whatsapp.net") {
		user := strings.TrimSuffix(req.Number, "@s.whatsapp.net")
		targetJID = types.NewJID(user, "s.whatsapp.net")
		fmt.Println("[Gateway] Destino padrao detectado.")
	} else {
		targetJID = types.NewJID(req.Number, "s.whatsapp.net")
		fmt.Println("[Gateway] Formato legado detectado.")
	}

	var msg proto.Message

	if req.Quoted != "" {
		participantStr := targetJID.String()
		msg = proto.Message{
			ExtendedTextMessage: &proto.ExtendedTextMessage{
				Text: &req.Text,
				ContextInfo: &proto.ContextInfo{
					StanzaID:      &req.Quoted,
					Participant:   &participantStr,
					QuotedMessage: &proto.Message{Conversation: &req.Text},
				},
			},
		}
	} else {
		msg = proto.Message{
			Conversation: &req.Text,
		}
	}

	_, err := waClient.SendMessage(context.Background(), targetJID, &msg)
	if err != nil {
		http.Error(w, fmt.Sprintf("WhatsMeow Error: %v", err), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status":"success"}`))
}

func presenceHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
}

func main() {
	logLevel := envOrDefault("LOG_LEVEL", "INFO")

	dbLog := waLog.Stdout("Database", logLevel, true)
	container, err := sqlstore.New(context.Background(), "sqlite3", "file:whatsmeow_session.db?_foreign_keys=on", dbLog)
	if err != nil {
		panic(err)
	}

	deviceStore, err := container.GetFirstDevice(context.Background())
	if err != nil {
		panic(err)
	}

	clientLog := waLog.Stdout("Client", logLevel, true)
	waClient = whatsmeow.NewClient(deviceStore, clientLog)
	waClient.AddEventHandler(waEventHandler)

	if waClient.Store.ID == nil {
		qrChan, _ := waClient.GetQRChannel(context.Background())
		err = waClient.Connect()
		if err != nil {
			panic(err)
		}
		for evt := range qrChan {
			if evt.Event == "code" {
				q, _ := qrcode.New(evt.Code, qrcode.Medium)
				fmt.Println(q.ToSmallString(false))
			}
		}
	} else {
		err = waClient.Connect()
		if err != nil {
			panic(err)
		}
	}

	go func() {
		http.HandleFunc("/send", sendHandler)
		http.HandleFunc("/presence", presenceHandler)
		if err := http.ListenAndServe(":3000", nil); err != nil {
			panic(err)
		}
	}()

	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	<-c
	waClient.Disconnect()
}
