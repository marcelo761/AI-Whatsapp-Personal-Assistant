def split_response(response: str, max_length: int = 4096) -> list[str]:
    if len(response) <= max_length:
        return [response]

    lines = response.splitlines()
    chunks: list[str] = []
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += "\n"
            current_chunk += line

    if current_chunk:
        chunks.append(current_chunk.strip())

    if not chunks:
        return [response[:max_length]]

    return chunks
