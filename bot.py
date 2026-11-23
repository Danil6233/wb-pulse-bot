import os
import json
import random
import asyncio
import urllib.parse
from datetime import datetime, timedelta

from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ⬇️ ВСТАВЬ СЮДА СВОИ ССЫЛКИ ⬇️
CHANNEL_URL = "https://t.me/pulse_biz_bots"
CONTACT_URL = "https://t.me/Danil88128"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

PRODUCTS = [
    {"sku": "HOME-01", "name": "Плед вязаный 200×220", "price": 2400, "cogs": 820, "base_qty": 12},
    {"sku": "HOME-02", "name": "Набор полотенец (3 шт)", "price": 1650, "cogs": 540, "base_qty": 15},
    {"sku": "HOME-03", "name": "Подушка ортопедическая", "price": 3100, "cogs": 1050, "base_qty": 8},
    {"sku": "HOME-04", "name": "Органайзер для белья", "price": 890, "cogs": 310, "base_qty": 14},
    {"sku": "HOME-05", "name": "Коврик для ванной", "price": 1250, "cogs": 480, "base_qty": 5},
    {"sku": "HOME-06", "name": "Корзина для хранения", "price": 1490, "cogs": 690, "base_qty": 2},
]

def generate_data():
    random.seed(42)
    today = (datetime.now() + timedelta(hours=3)).date()
    sales = []

    for day_offset in range(29, -1, -1):
        d = today - timedelta(days=day_offset)
        weekend_boost = 1.2 if d.weekday() >= 5 else 1.0

        for p in PRODUCTS:
            for mp in ["WB", "Ozon"]:
                mp_share = 0.65 if mp == "WB" else 0.35
                qty = max(0, int(round(p["base_qty"] * mp_share * weekend_boost * random.uniform(0.75, 1.3))))
                if qty == 0:
                    continue

                orders_rub = qty * p["price"]
                cogs_rub = qty * p["cogs"]
                comm_rate = 0.19 if mp == "WB" else 0.17
                commission_rub = int(orders_rub * comm_rate)
                logistics_rub = qty * (165 if mp == "WB" else 180)
                ads_rate = 0.22 if p["sku"] == "HOME-06" else random.uniform(0.06, 0.10)
                ads_rub = int(orders_rub * ads_rate)
                profit_rub = orders_rub - cogs_rub - commission_rub - logistics_rub - ads_rub

                sales.append({
                    "date": d,
                    "marketplace": mp,
                    "product_name": p["name"],
                    "orders_qty": qty,
                    "orders_rub": orders_rub,
                    "ads_rub": ads_rub,
                    "profit_rub": profit_rub,
                })

    stocks = [
        {"mp": "WB", "name": "Плед вязаный 200×220", "stock": 26, "avg_day": 9.2, "transit": 120},
        {"mp": "WB", "name": "Набор полотенец (3 шт)", "stock": 31, "avg_day": 11.5, "transit": 0},
        {"mp": "Ozon", "name": "Подушка ортопедическая", "stock": 42, "avg_day": 3.1, "transit": 50},
        {"mp": "WB", "name": "Органайзер для белья", "stock": 145, "avg_day": 9.8, "transit": 0},
        {"mp": "Ozon", "name": "Коврик для ванной", "stock": 88, "avg_day": 1.9, "transit": 0},
        {"mp": "WB", "name": "Корзина для хранения", "stock": 114, "avg_day": 1.2, "transit": 0},
    ]
    for s in stocks:
        s["days_left"] = round(s["stock"] / s["avg_day"], 1)

    return sales, stocks

SALES, STOCKS = generate_data()
LIVE_BOOST = 0

def fmt(num):
    return f"{int(round(num)):,}".replace(",", " ")

def progress_bar(pct):
    filled = min(10, max(0, int(round(pct / 10))))
    return "🟩" * filled + "⬜" * (10 - filled)

def get_main_kb():
    crit_count = sum(1 for s in STOCKS if s["days_left"] <= 4.0)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 График за 7 дней", callback_data="chart"),
            InlineKeyboardButton(text=f"⚠️ Остатки ({crit_count})", callback_data="stocks"),
        ],
        [
            InlineKeyboardButton(text="🏆 Топ / Антитоп", callback_data="top"),
            InlineKeyboardButton(text="🟣 WB / 🔵 Ozon", callback_data="split"),
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить данные", callback_data="refresh"),
        ],
        [
            InlineKeyboardButton(text="💼 Тарифы и заказ такого бота", callback_data="tariffs"),
        ],
        [
            InlineKeyboardButton(text="📢 Канал с проектами", url=CHANNEL_URL),
            InlineKeyboardButton(text="💬 Связаться", url=CONTACT_URL),
        ]
    ])

def get_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к сводке", callback_data="summary")]
    ])

def get_tariffs_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Обсудить проект / Заказать", url=CONTACT_URL)],
        [InlineKeyboardButton(text="📢 Другие проекты в канале", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="⬅️ Назад к сводке", callback_data="summary")],
    ])

def build_summary_text():
    today = max(r["date"] for r in SALES)
    today_rows = [r for r in SALES if r["date"] == today]

    orders_rub = sum(r["orders_rub"] for r in today_rows) + LIVE_BOOST * 2400
    orders_qty = sum(r["orders_qty"] for r in today_rows) + LIVE_BOOST
    profit_rub = sum(r["profit_rub"] for r in today_rows) + LIVE_BOOST * 590
    ads_rub = sum(r["ads_rub"] for r in today_rows) + LIVE_BOOST * 180

    margin = (profit_rub / orders_rub * 100) if orders_rub else 0
    drr = (ads_rub / orders_rub * 100) if orders_rub else 0
    drr_status = "в норме" if drr <= 10 else "высокий"

    month_orders = sum(r["orders_rub"] for r in SALES) + LIVE_BOOST * 2400
    plan_rub = 3_500_000
    plan_pct = min(100, int(month_orders / plan_rub * 100))

    wb_rub = sum(r["orders_rub"] for r in today_rows if r["marketplace"] == "WB") + LIVE_BOOST * 2400
    wb_qty = sum(r["orders_qty"] for r in today_rows if r["marketplace"] == "WB") + LIVE_BOOST
    oz_rub = sum(r["orders_rub"] for r in today_rows if r["marketplace"] == "Ozon")
    oz_qty = sum(r["orders_qty"] for r in today_rows if r["marketplace"] == "Ozon")

    crit_count = sum(1 for s in STOCKS if s["days_left"] <= 4.0)
    now_str = (datetime.now() + timedelta(hours=3)).strftime("%d.%m · %H:%M МСК")

    return (
        f"<b>📊 ПУЛЬС БИЗНЕСА | {now_str}</b>\n"
        f"<i>Магазин: Товары для дома (WB + Ozon)</i>\n\n"
        f"💰 <b>Заказы сегодня:</b> <code>{fmt(orders_rub)} ₽</code> ({orders_qty} шт)\n"
        f"📈 <b>Чистая прибыль:</b> <code>~{fmt(profit_rub)} ₽</code> <i>(маржа {margin:.1f}%)</i>\n"
        f"📢 <b>Реклама (ДРР):</b> <code>{fmt(ads_rub)} ₽</code> <i>({drr:.1f}% — {drr_status})</i>\n\n"
        f"<b>План месяца</b> <i>({fmt(plan_rub)} ₽)</i>:\n"
        f"{progress_bar(plan_pct)} <b>{plan_pct}%</b> <i>({fmt(month_orders)} ₽)</i>\n\n"
        f"<b>Разбивка по площадкам:</b>\n"
        f"🟣 <b>WB:</b> <code>{fmt(wb_rub)} ₽</code> · {wb_qty} шт\n"
        f"🔵 <b>Ozon:</b> <code>{fmt(oz_rub)} ₽</code> · {oz_qty} шт\n\n"
        f"⚠️ <b>Требует внимания:</b> {crit_count} хита продаж закончатся через 3 дня."
    )

def build_stocks_text():
    crit = sorted([s for s in STOCKS if s["days_left"] <= 4.0], key=lambda x: x["days_left"])
    over = sorted([s for s in STOCKS if s["days_left"] >= 45.0], key=lambda x: x["days_left"], reverse=True)

    lines = ["<b>⚠️ КОНТРОЛЬ ОСТАТКОВ</b>\n", "<b>🔴 Критично (меньше 4 дней):</b>"]
    for r in crit:
        transit_note = f"🚚 в пути {r['transit']} шт" if r["transit"] > 0 else "❗️ поставка не создана"
        lines.append(
            f"• <b>{r['name']}</b> ({r['mp']})\n"
            f"  Остаток: <code>{r['stock']} шт</code> · хватит на <b>{r['days_left']} дн.</b> ({transit_note})"
        )

    lines.append("\n<b>🟡 Замороженные деньги (хватит более чем на 45 дней):</b>")
    for r in over:
        lines.append(
            f"• <b>{r['name']}</b> ({r['mp']})\n"
            f"  Остаток: <code>{r['stock']} шт</code> · ~{int(r['days_left'])} дн. (платное хранение)"
        )
    return "\n".join(lines)

def build_top_text():
    stats = {}
    for r in SALES:
        name = r["product_name"]
        if name not in stats:
            stats[name] = {"name": name, "orders_rub": 0, "profit_rub": 0, "orders_qty": 0}
        stats[name]["orders_rub"] += r["orders_rub"]
        stats[name]["profit_rub"] += r["profit_rub"]
        stats[name]["orders_qty"] += r["orders_qty"]

    items = list(stats.values())
    for it in items:
        it["margin"] = round(it["profit_rub"] / it["orders_rub"] * 100, 1) if it["orders_rub"] else 0

    top3 = sorted(items, key=lambda x: x["profit_rub"], reverse=True)[:3]
    anti = sorted(items, key=lambda x: x["profit_rub"])[:2]

    lines = ["<b>🏆 ТОП И АНТИТОП ЗА 30 ДНЕЙ</b>\n", "<b>🔥 Локомотивы прибыли:</b>"]
    for i, r in enumerate(top3, 1):
        lines.append(
            f"{i}. <b>{r['name']}</b>\n"
            f"   Прибыль: <code>+{fmt(r['profit_rub'])} ₽</code> · маржа {r['margin']}%"
        )

    lines.append("\n<b>🧊 Тянут вниз (низкая отдача / высокий ДРР):</b>")
    for r in anti:
        lines.append(
            f"• <b>{r['name']}</b>\n"
            f"  Прибыль: <code>{fmt(r['profit_rub'])} ₽</code> · маржа {r['margin']}% ({r['orders_qty']} шт)"
        )
    return "\n".join(lines)

def build_split_text():
    lines = ["<b>🟣 WILDBERRIES vs 🔵 OZON (30 дней)</b>\n"]
    for mp, icon in [("WB", "🟣"), ("Ozon", "🔵")]:
        rows = [r for r in SALES if r["marketplace"] == mp]
        orders_rub = sum(r["orders_rub"] for r in rows)
        profit_rub = sum(r["profit_rub"] for r in rows)
        ads_rub = sum(r["ads_rub"] for r in rows)
        orders_qty = sum(r["orders_qty"] for r in rows)
        margin = profit_rub / orders_rub * 100
        drr = ads_rub / orders_rub * 100
        avg_check = orders_rub / orders_qty
        lines.append(
            f"{icon} <b>{mp}</b>\n"
            f"├ Заказы: <code>{fmt(orders_rub)} ₽</code> ({orders_qty} шт)\n"
            f"├ Чистая прибыль: <code>{fmt(profit_rub)} ₽</code> (маржа {margin:.1f}%)\n"
            f"├ Средний чек: <code>{fmt(avg_check)} ₽</code>\n"
            f"└ ДРР: <code>{drr:.1f}%</code>\n"
        )
    return "\n".join(lines)

def build_tariffs_text():
    return (
        "<b>💼 АКТУАЛЬНЫЕ ТАРИФЫ НА РАЗРАБОТКУ</b>\n"
        "<i>Соберу аналогичного бота под ваши цифры и задачи.</i>\n\n"
        "<b>1️⃣ Старт — от 12 000 ₽</b> <i>(3–5 дней)</i>\n"
        "• Подключение к Google Таблицам или Excel-выгрузкам\n"
        "• Главная сводка: выручка, прибыль, план месяца\n"
        "• Базовые кнопки и графики\n\n"
        "<b>2️⃣ Бизнес под ключ — от 25 000 ₽</b> <i>(7–10 дней)</i>\n"
        "• Прямая интеграция по API (WB, Ozon, 1С, МойСклад, CRM)\n"
        "• Автоматические утренние отчёты и алерты по остаткам\n"
        "• Разбивка по точкам/площадкам, топ и антитоп\n\n"
        "<b>3️⃣ Поддержка 24/7 — 3 000 ₽/мес</b>\n"
        "• Хостинг, мониторинг стабильности и мелкие доработки\n\n"
        "👇 <i>Напишите в личку — бесплатно разберём вашу задачу и сделаем мини-прототип.</i>"
    )

def build_chart_url():
    dates = sorted(set(r["date"] for r in SALES))[-7:]
    labels = [d.strftime("%d.%m") for d in dates]
    orders_k = [round(sum(r["orders_rub"] for r in SALES if r["date"] == d) / 1000) for d in dates]
    profit_k = [round(sum(r["profit_rub"] for r in SALES if r["date"] == d) / 1000) for d in dates]

    chart_cfg = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "type": "line",
                    "label": "Чистая прибыль (тыс. ₽)",
                    "borderColor": "#10B981",
                    "backgroundColor": "rgba(16, 185, 129, 0.15)",
                    "borderWidth": 3,
                    "fill": True,
                    "tension": 0.3,
                    "data": profit_k
                },
                {
                    "type": "bar",
                    "label": "Заказы (тыс. ₽)",
                    "backgroundColor": "#6366F1",
                    "borderRadius": 6,
                    "data": orders_k
                }
            ]
        },
        "options": {
            "plugins": {
                "title": {"display": True, "text": "Динамика за 7 дней (WB + Ozon)", "color": "#F8FAFC", "font": {"size": 16}},
                "legend": {"labels": {"color": "#E2E8F0"}}
            },
            "scales": {
                "x": {"ticks": {"color": "#94A3B8"}, "grid": {"color": "rgba(148,163,184,0.12)"}},
                "y": {"ticks": {"color": "#94A3B8"}, "grid": {"color": "rgba(148,163,184,0.12)"}}
            }
        }
    }
    encoded = urllib.parse.quote(json.dumps(chart_cfg))
    return f"https://quickchart.io/chart?v=4&w=800&h=450&bkg=%230F172A&c={encoded}"

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(build_summary_text(), reply_markup=get_main_kb())

@dp.callback_query(F.data == "summary")
async def cb_summary(callback: types.CallbackQuery):
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(build_summary_text(), reply_markup=get_main_kb())
    else:
        await callback.message.edit_text(build_summary_text(), reply_markup=get_main_kb())
    await callback.answer()

@dp.callback_query(F.data == "refresh")
async def cb_refresh(callback: types.CallbackQuery):
    global LIVE_BOOST
    LIVE_BOOST += random.randint(1, 3)
    await callback.message.edit_text(build_summary_text(), reply_markup=get_main_kb())
    await callback.answer("Данные обновлены! Прилетели новые заказы ✅")

@dp.callback_query(F.data == "stocks")
async def cb_stocks(callback: types.CallbackQuery):
    await callback.message.edit_text(build_stocks_text(), reply_markup=get_back_kb())
    await callback.answer()

@dp.callback_query(F.data == "top")
async def cb_top(callback: types.CallbackQuery):
    await callback.message.edit_text(build_top_text(), reply_markup=get_back_kb())
    await callback.answer()

@dp.callback_query(F.data == "split")
async def cb_split(callback: types.CallbackQuery):
    await callback.message.edit_text(build_split_text(), reply_markup=get_back_kb())
    await callback.answer()

@dp.callback_query(F.data == "tariffs")
async def cb_tariffs(callback: types.CallbackQuery):
    await callback.message.edit_text(build_tariffs_text(), reply_markup=get_tariffs_kb())
    await callback.answer()

@dp.callback_query(F.data == "chart")
async def cb_chart(callback: types.CallbackQuery):
    await callback.answer("Рисую график...")
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=build_chart_url(),
        caption="<b>📈 Динамика заказов и чистой прибыли за 7 дней</b>\n<i>Синие столбцы — заказы, зеленая линия — чистая прибыль.</i>",
        reply_markup=get_back_kb()
    )

async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Веб-сервер запущен на порту {port}", flush=True)

async def main():
    await start_web_server()
    print("🚀 Бот «Пульс бизнеса» запущен на Render!", flush=True)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
