"""llm.py — one small wrapper around the model. Two backends, same functions:
- Groq (free cloud API, used when GROQ_API_KEY is set). Key from console.groq.com
- Ollama + llama3.2 on this laptop (no key, nothing leaves the laptop). Setup once:  ollama pull llama3.2"""
import json
import os

OPTIONS = {"temperature": 0, "seed": 42}  # same question → same answer, so the class sees the same thing

if os.environ.get("GROQ_API_KEY"):
    import groq

    BACKEND = "Groq"
    MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")     # see console.groq.com/docs/models for the free list
    client = groq.Groq()                                           # reads GROQ_API_KEY

    def chat(messages, schema=None, limit=None):
        """`schema` asks for JSON matching a pydantic model. Groq is told the schema; the caller validates the reply."""
        if schema:
            note = {"role": "system", "content": f"Reply with only a JSON object matching this JSON schema:\n{json.dumps(schema.model_json_schema())}"}
            messages = [note] + messages
        try:
            reply = client.chat.completions.create(model=MODEL, messages=messages, **OPTIONS,
                                                   response_format={"type": "json_object"} if schema else None)
        except groq.BadRequestError as e:
            recovered = recover_json(e) if schema else None
            if recovered:
                return recovered
            raise ConnectionError(f"Groq: {e}") from e
        except groq.APIError as e:                                 # bad key, rate limit, no internet…
            raise ConnectionError(f"Groq: {e}") from e
        return reply.choices[0].message.content

    def recover_json(e):
        """Some models answer JSON as a tool call and Groq refuses it (tool_use_failed) — but its error carries the JSON.
        The caller still validates it, so a bad reply is rejected as usual."""
        error = e.body.get("error", e.body) if isinstance(e.body, dict) else {}
        if error.get("code") != "tool_use_failed":
            return None
        try:
            generated = json.loads(error.get("failed_generation", ""))
        except json.JSONDecodeError:
            return None
        if not isinstance(generated, dict):
            return None
        arguments = generated.get("arguments", generated)
        return arguments if isinstance(arguments, str) else json.dumps(arguments)
else:
    import ollama

    BACKEND = "Ollama"
    MODEL = "llama3.2"                      # on a 4 GB laptop use "llama3.2:1b"

    def chat(messages, schema=None, limit=None):
        options = {**OPTIONS, "num_predict": limit} if limit else OPTIONS
        return ollama.chat(model=MODEL, messages=messages, options=options,
                           format=schema.model_json_schema() if schema else None).message.content


def ask(prompt, system=None):
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    return chat(messages).strip()


def ask_json(prompt, schema):
    """Ask for JSON that must match a pydantic model; returns a validated object (or raises)."""
    return schema.model_validate_json(chat([{"role": "user", "content": prompt}], schema=schema))
