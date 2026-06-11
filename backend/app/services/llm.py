import anthropic
from app.config import settings
from app.core.logger import get_logger
import json
import re

logger = get_logger(__name__)

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-sonnet-4-5"

def call_claude(
    prompt: str,
    system_prompt: str = None,
    max_tokens: int = 1000,
    temperature: float = 0.3
) -> dict:
    logger.info(f"Calling Claude API — prompt length: {len(prompt)} chars")
    messages = [{"role": "user", "content": prompt}]
    kwargs = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system_prompt:
        kwargs["system"] = system_prompt
    response = client.messages.create(**kwargs)
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost_usd = (input_tokens * 0.000003) + (output_tokens * 0.000015)
    result = {
        "content": response.content[0].text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": round(cost_usd, 6),
        "model": MODEL,
        "stop_reason": response.stop_reason,
    }
    logger.info(
        f"Claude response — tokens: {result['total_tokens']}, "
        f"cost: ${result['cost_usd']}"
    )
    return result

def validate_numbers_in_response(response_text: str, source_data: dict) -> dict:
    validation_result = {
        "passed": True,
        "issues": [],
        "numbers_checked": 0,
        "numbers_validated": 0,
    }
    numbers_in_response = re.findall(r'\b\d+(?:\.\d+)?\b', response_text)
    validation_result["numbers_checked"] = len(numbers_in_response)
    source_numbers = set()
    for key, value in source_data.items():
        if isinstance(value, (int, float)):
            source_numbers.add(str(round(value, 2)))
            source_numbers.add(str(int(value)))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    for k, v in item.items():
                        if isinstance(v, (int, float)):
                            source_numbers.add(str(round(v, 2)))
                            source_numbers.add(str(int(v)))
    significant_numbers = [
        n for n in numbers_in_response
        if float(n) > 100
    ]
    for number in significant_numbers:
        if number in source_numbers:
            validation_result["numbers_validated"] += 1
        else:
            found_close = False
            for source_num in source_numbers:
                try:
                    if abs(float(number) - float(source_num)) < 1:
                        found_close = True
                        validation_result["numbers_validated"] += 1
                        break
                except ValueError:
                    continue
            if not found_close and float(number) > 100:
                validation_result["issues"].append({
                    "number": number,
                    "issue": "Could not verify against source data"
                })
    if len(validation_result["issues"]) > 3:
        validation_result["passed"] = False
        logger.warning(
            f"Hallucination check failed — "
            f"{len(validation_result['issues'])} unverified numbers"
        )
    else:
        logger.info(
            f"Hallucination check passed — "
            f"{validation_result['numbers_validated']}/"
            f"{validation_result['numbers_checked']} numbers verified"
        )
    return validation_result

def build_system_prompt():
    return """You are an AI operations analyst for a food services company 
operating cafeterias across university campuses in Toronto, Canada.

Your role is to analyze operational data and provide clear, actionable 
insights to campus managers. You speak plainly and directly.

Guidelines:
- Use only the data provided to you. Never invent numbers.
- Be specific and actionable. Avoid vague statements.
- Highlight what needs immediate attention first.
- Keep recommendations practical and achievable.
- Format your response clearly with sections.
- Always include specific numbers from the data provided.
- Flag any concerning trends proactively."""