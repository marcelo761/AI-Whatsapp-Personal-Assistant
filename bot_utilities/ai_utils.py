import json
import logging
import os

from dotenv import load_dotenv
from googleapiclient.discovery import build
from openai import AsyncOpenAI

from bot_utilities.config_loader import config

load_dotenv()

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("API_KEY")
        if not api_key:
            raise RuntimeError("API_KEY nao configurada no ambiente.")
        _client = AsyncOpenAI(
            base_url=config["API_BASE_URL"],
            api_key=api_key,
        )
    return _client


async def generate_response(instructions: str, history: list[dict[str, str]]) -> str:
    client = _get_client()

    system_instruction = (
        f"{instructions}\n\n"
        "CRITICAL: You possess a native function called 'searchtool'.\n"
        "If you need current events, live data, real-time prices, or anything about the year 2026, you MUST invoke 'searchtool'.\n"
        "IMPORTANT: When you decide to call 'searchtool', you MUST ONLY output the tool call JSON structure. "
        "Do NOT write any conversational text, greetings, explanations, or thoughts before or after the tool call. "
        "Any text mixed with the tool call will break the system. Be direct and output the JSON tool call silently.\n"
        "GLOBAL CONTEXT RULE: Analyze the entire chat history to construct a rich, complete, and explicit search query whenever follow-up or vague questions are asked.\n"
        "ANALYSIS RULE: Read all search snippets carefully before formulating your final user response."
    )
    messages = [
        {"role": "system", "content": system_instruction},
        *history,
    ]

    available_functions = {
        "searchtool": google_search_tool,
    }

    search_tool_definition = {
        "type": "function",
        "function": {
            "name": "searchtool",
            "description": "Search the web for up-to-date information, news, and prices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        },
    }

    try:
        response = await client.chat.completions.create(
            model=config["MODEL_ID"],
            messages=messages,
            tools=[search_tool_definition],
            tool_choice="auto",
            max_tokens=1024,
        )
    except Exception as api_err:
        logger.error("Initial AI call failed: %s", api_err)
        try:
            response = await client.chat.completions.create(
                model=config["MODEL_ID"],
                messages=messages,
                tool_choice="none",
                max_tokens=1024,
            )
        except Exception as fallback_err:
            logger.error("AI fallback call failed: %s", fallback_err)
            return "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente."

    msg = response.choices[0].message

    if msg.tool_calls:
        logger.debug("The model requested a search tool call")
        messages.append(msg)

        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments)
            except Exception as parse_err:
                logger.error("Failed to parse tool arguments: %s", parse_err)
                continue

            if func_name in available_functions:
                logger.debug("Running Google search for: %s", func_args.get("query"))
                func_result = await available_functions[func_name](**func_args)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": func_result,
                    }
                )

                followup = await client.chat.completions.create(
                    model=config["MODEL_ID"],
                    messages=messages,
                    tools=[search_tool_definition],
                    tool_choice="none",
                    temperature=0.5,
                    max_tokens=1024,
                )

                final_text = followup.choices[0].message.content or func_result
                logger.debug("Final AI response generated after search")
                return final_text

        return msg.content or "Nao foi possivel processar a solicitacao."

    logger.debug("AI responded without search")
    return msg.content or "Nao foi possivel gerar uma resposta."


async def google_search_tool(query: str) -> str:
    if not config["INTERNET_ACCESS"]:
        return "Acesso a internet foi desabilitado."

    blob = ""
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        logger.warning("Google Search credentials not configured")
        return "Busca na web indisponivel no momento."

    try:
        service = build("customsearch", "v1", developerKey=api_key)
        res = service.cse().list(q=query, cx=cse_id, num=10).execute()
        results = res.get("items", [])
        for index, result in enumerate(results):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            blob += f"[{index}] Titulo: {title}\nResumo: {snippet}\n\n"
        if not blob:
            blob = "Nenhum resultado encontrado."
    except Exception as exc:
        logger.exception("Google search failed")
        blob = f"Erro na busca: {exc}"

    return blob
