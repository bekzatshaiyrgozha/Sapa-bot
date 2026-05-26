import json
import logging
from openai import OpenAI
from bot import config
from typing import Dict

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Сен — JUZ40 онлайн мектебінің оқу презентацияларын тексеретін қатаң автоматты тексеруші.
Мұғалімнің презентациясын регламент критерийлері бойынша тексеріп, ТЕК JSON форматында жауап қайтар.
 
Презентация мәтіні әр бет бойынша келесідей белгіленеді:
=== СЛАЙД 1 ===
[слайд мәтіні]
=== СЛАЙД 2 ===
[слайд мәтіні]
...
 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ТЕКСЕРУ КРИТЕРИЙЛЕРІ (7 критерий):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 
1. САБАҚ МАҚСАТЫ (Цель урока)
   - Алғашқы слайдтардың бірінде сабақ мақсаты болуы тиіс
   - Қазақша немесе орысша жазылуы мүмкін
   - Мына жағдайлардың кез келгені болса → status = "OK":
     * "мақсат", "цель", "бүгін біз білеміз", "оқушылар біледі", "үйренеміз" деген сөздер
     * Слайдта "МАҚСАТ" тақырыбы бар және кем дегенде бір мазмұндық сөйлем бар
     * Мақсат бір сөйлеммен де болса жеткілікті
   - Тек "МАҚСАТ" деген сөз жалғыз тұрса және астында мазмұн жоқ болса ғана → status = "MISSING"
 
2. САБАҚ ЖОСПАРЫ (План урока / Күн тәртібі)
   - Сабақтың жоспары немесе күн тәртібі болуы тиіс
   - Негізгі сөздер: "жоспар", "план", "күн тәртібі", "agenda" т.б.
 
3. ЫНТАЛАНДЫРУ (Мотивация)
   - Ынталандыратын мазмұн болуы тиіс. Бұл критерийді КЕҢ АУҚЫМДА бағала.
   - Міндетті түрде "мотивация" немесе "ынталандыру" деген сөз болуы ШАРТ ЕМЕС.
   - Мына жағдайлардың кез келгені болса → status = "OK":
     * Мотивациялық немесе шабыттандырушы сөйлем/мақал-мәтел (мысалы: "Жақсы нәтиже үлкен еңбекті талап етеді!")
     * Танымал адамның дәйексөзі немесе нақыл сөз
     * Оқушыны ойлануға шақыратын риторикалық сұрақ
     * Қызықты факт немесе тарихи мысал
     * "мотивация", "ынталандыру", "цитата", "мақал" деген сөздер
     * Жігерлендіретін, шабыттандыратын кез келген мәтін
   - Тек мүлдем бос немесе тақырыптық мазмұны жоқ болса ғана → status = "MISSING"
 
4. ТАҚЫРЫПТЫҢ ТОЛЫҚТЫҒЫ (Полнота темы)
   - Сабақ тақырыбы жеткілікті толық ашылуы тиіс
   - Бос немесе аз мәтінді слайдтар болмауы керек (5 сөзден аз)
   - Материал тақырыппен логикалық байланысты болуы тиіс
 
5. БОНУС ЕСЕП (Бонусное задание)
   - Кемінде бір бонустық тапсырма немесе күрделі сұрақ болуы тиіс
   - Негізгі сөздер: "бонус", "bonus", "қосымша есеп", "дополнительное задание" т.б.
 
6. ОРФОГРАФИЯ ЖӘНЕ ГРАММАТИКА
   - ӨРЕСКЕЛ орфографиялық және грамматикалық қателерді тексер
   - Қате слайдтың нақты нөмірін, қате сөзді және дұрыс нұсқасын көрсет
 
7. ЖАЛПЫ ҚҰРЫЛЫМ (Структура)
   - Титулдық слайдтың болуы (әдетте 1-слайд)
   - Логикалық реттілік: кіріспе → негізгі бөлім → қорытынды
 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ЕРЕЖЕЛЕР:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- overall_status = "PASSED" тек барлық 7 критерий OK болғанда ғана
- Кем дегенде бір критерий MISSING/INCOMPLETE/HAS_ERRORS/ISSUES болса → overall_status = "FAILED"
- summary қазақ тілінде жаз, қысқаша (2-3 сөйлем)
- slide_number — элемент табылған/табылмаған слайд нөмірін көрсет (немесе null)
 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ЖАУАП ФОРМАТЫ — ТІКЕЛЕЙ JSON (markdown жоқ, ```json жоқ, алдында/артында түсіндірме жоқ):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "total_slides": <сан>,
  "overall_status": "PASSED" | "FAILED",
  "criteria": {
    "lesson_goal": {
      "status": "OK" | "MISSING",
      "comment": "...",
      "slide_number": <сан немесе null>
    },
    "lesson_plan": {
      "status": "OK" | "MISSING",
      "comment": "...",
      "slide_number": <сан немесе null>
    },
    "motivation": {
      "status": "OK" | "MISSING",
      "comment": "...",
      "slide_number": <сан немесе null>
    },
    "topic_coverage": {
      "status": "OK" | "INCOMPLETE",
      "comment": "..."
    },
    "bonus_task": {
      "status": "OK" | "MISSING",
      "comment": "...",
      "slide_number": <сан немесе null>
    },
    "spelling": {
      "status": "OK" | "HAS_ERRORS",
      "errors": [
        {"slide_number": <N>, "word": "қате сөз", "suggestion": "дұрыс нұсқа"}
      ]
    },
    "structure": {
      "status": "OK" | "ISSUES",
      "comment": "..."
    }
  },
  "summary": "Қазақ тіліндегі қысқаша қорытынды"
}
"""


def check_presentation(slide_text: str) -> Dict:
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in config")

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Мына презентацияны тексер:\n\n{slide_text}"}
            ],
            max_tokens=2000,
            temperature=0,
        )
    except Exception as e:
        logger.exception("OpenAI API қоңырауы сәтсіз: %s", e)
        raise

    content = resp.choices[0].message.content
    logger.info("AI жауабы (алғашқы 500): %s", content[:500] if content else "БОС")

    if not content or content.strip() == "":
        return {
            "total_slides": 0,
            "overall_status": "FAILED",
            "criteria": {},
            "summary": "ЖИ бос жауап қайтарды. Файлды қайта жүктеп көріңіз."
        }

    try:
        data = json.loads(content.strip())
        logger.info("Парсинг сәтті: overall_status=%s", data.get("overall_status"))
        return data
    except Exception:
        pass

    start = content.find('{')
    end = content.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(content[start:end + 1])
            logger.info("Substring парсинг сәтті: overall_status=%s", data.get("overall_status"))
            return data
        except Exception as e:
            logger.warning("Substring парсинг сәтсіз: %s", e)

    snippet = content[:2000] if isinstance(content, str) else str(content)
    logger.warning("AI дұрыс JSON қайтармады.")
    return {
        "total_slides": 0,
        "overall_status": "FAILED",
        "criteria": {},
        "summary": "ЖИ дұрыс формат қайтармады. Әкімшіге хабарласыңыз.",
        "raw_response": snippet
    }


def format_ai_result(ai_result: Dict) -> str:
    """AI нәтижесін мұғалімге қазақша форматта жібереді."""
    if not ai_result or not isinstance(ai_result, dict):
        return "❌ Тексеру сәтсіз аяқталды. Файлды қайта жүктеп көріңіз."

    if "raw_response" in ai_result and not ai_result.get("criteria"):
        return (
            "⚠️ ЖИ оқылмайтын жауап қайтарды.\n"
            f"Үзінді: {ai_result['raw_response'][:300]}"
        )

    total = ai_result.get("total_slides", "?")
    overall = ai_result.get("overall_status", "FAILED")
    criteria = ai_result.get("criteria", {})
    summary = ai_result.get("summary", "")

    STATUS_ICONS = {
        "OK": "✅",
        "MISSING": "❌",
        "INCOMPLETE": "⚠️",
        "HAS_ERRORS": "⚠️",
        "ISSUES": "⚠️",
    }

    CRITERIA_LABELS = {
        "lesson_goal":    "Сабақ мақсаты",
        "lesson_plan":    "Сабақ жоспары",
        "motivation":     "Ынталандыру",
        "topic_coverage": "Тақырыптың толықтығы",
        "bonus_task":     "Бонус есеп",
        "spelling":       "Орфография",
        "structure":      "Құрылым",
    }

    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📊 ЖИ ТЕКСЕРУ НӘТИЖЕСІ")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📄 Барлық слайд саны: {total}")
    lines.append("✅ ӨТТІ" if overall == "PASSED" else "❌ ӨТПЕДІ")
    lines.append("")
    lines.append("📋 КРИТЕРИЙЛЕР БОЙЫНША:")

    for key, label in CRITERIA_LABELS.items():
        crit = criteria.get(key)
        if not crit:
            lines.append(f"⬜ {label} — деректер жоқ")
            continue

        status = crit.get("status", "")
        icon = STATUS_ICONS.get(status, "⬜")
        comment = crit.get("comment", "")
        slide_num = crit.get("slide_number")

        if key == "spelling":
            errors = crit.get("errors", [])
            if status == "OK":
                lines.append(f"✅ {label} — қате табылмады")
            else:
                lines.append(f"⚠️ {label} — қателер табылды:")
                for err in errors:
                    sn = err.get("slide_number", "?")
                    word = err.get("word", "")
                    suggestion = err.get("suggestion", "")
                    lines.append(f"   • {sn}-слайд: «{word}» → «{suggestion}»")
        else:
            slide_info = f" ({slide_num}-слайд)" if slide_num else ""
            lines.append(f"{icon} {label}{slide_info} — {comment}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📝 Қорытынды: {summary}")

    if overall == "FAILED":
        lines.append("")
        lines.append("⚠️ Ескертулерді түзетіп, файлды қайта жүктеңіз.")
        lines.append("Түзетілмейінше — жүйеде ОРЫНДАЛМАДЫ деп белгіленеді.")

    return "\n".join(lines)