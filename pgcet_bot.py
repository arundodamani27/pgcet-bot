from dotenv import load_dotenv
load_dotenv()

# ✅ Imports
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import csv
from rank_data import rawMCA, rawMBA
import os
import requests
from bs4 import BeautifulSoup

# ✅ Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ✅ Save user info to CSV
def save_user(user):
    user_id = user.id
    user_name = user.first_name or "User"
    file_path = "pgcet_users.csv"
    already_exists = os.path.isfile(file_path)

    with open(file_path, "a", newline="") as file:
        writer = csv.writer(file)
        if not already_exists:
            writer.writerow(["user_id", "user_name"])
        writer.writerow([user_id, user_name])

# ✅ KEA scraping
def get_latest_kea_update():
    try:
        url = "https://cetonline.karnataka.gov.in/kea/"
        response = requests.get(url, timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table", id="ContentPlaceHolder1_Gridlatestannoc")
        if not table:
            return "ℹ️ No recent announcements found."

        rows = table.find_all("tr")[:5]
        if not rows:
            return "ℹ️ No announcements available."

        updates = ""
        for row in rows:
            link = row.find("a")
            if link:
                title = link.get_text(strip=True)
                updates += f"🔸 {title}\n\n"

        return updates.strip()

    except Exception as e:
        return f"⚠️ Error fetching KEA updates: {e}"


# ✅ /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    user_name = user.first_name or "there"
    welcome_text = (
        f"👋 Hello *{user_name}*, welcome to *PGCET Helper Bot*! 🎓\n\n"
        "Use the following commands to access resources:\n\n"
        "📊 /cutoffs – View MCA & MBA PGCET 2024 Cutoffs\n"
        "📚 /syllabus – Download Syllabus PDFs\n"
        "🎓 /colleges – View colleges by district\n"
        "📢 /kea – Get recent KEA updates\n"
        "📈 /predict – Predict rank by your marks\n"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# ✅ /cutoffs
async def cutoffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 *MCA & MBA PGCET Cutoffs 2024*:\n\n"
        "📄 /mca_cutoff – Download MCA Cutoff PDF\n"
        "📄 /mba_cutoff – Download MBA Cutoff PDF",
    )
# ✅ /mca_cutoff and /mba_cutoff
async def mca_cutoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_document(open("mca_cutoff.pdf", "rb"), filename="MCA_Cutoff.pdf")

async def mba_cutoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_document(open("mba_cutoff.pdf", "rb"), filename="MBA_Cutoff.pdf")



# ✅ /syllabus
async def syllabus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 /mca_syllabus – Download MCA Syllabus\n"
        "📕 /mba_syllabus – Download MBA Syllabus"
    )

# ✅ /mca_syllabus and /mba_syllabus
async def mca_syllabus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_document(open("mca_syllabus.pdf", "rb"), filename="MCA_Syllabus.pdf")

async def mba_syllabus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_document(open("mba_syllabus.pdf", "rb"), filename="MBA_Syllabus.pdf")

# ✅ /kea
async def kea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    latest = get_latest_kea_update()
    await update.message.reply_text(f"📢 *KEA Recent Updates:*\n\n{latest}", parse_mode='Markdown')

# ✅ /colleges (asks for district input)
district_colleges = {
    "mangalore": {
        "MCA": ["St Joseph Engineering College", "Sahyadri College", "Canara Engineering College"],
        "MBA": ["A J Institute of Management", "St Aloysius Institute of Management & Information Technology"]
    },
    "bangalore": {
        "MCA": ["RV College", "MSRIT", "BMSCE"],
        "MBA": ["Christ University", "PES University", "Alliance University"]
    }
}

async def colleges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏙️ Enter your *district name* to see MCA colleges accepting PGCET:",
        parse_mode='Markdown'
    )
    context.user_data["awaiting_district"] = True

async def handle_district_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_district"):
        district = update.message.text.strip().lower()
        course = "MCA"
        colleges = district_colleges.get(district, {}).get(course)

        if colleges:
            reply = f"🏫 *{course} Colleges accepting PGCET in {district.title()}*:\n\n"
            for clg in colleges:
                reply += f"🔸 {clg}\n"
        else:
            reply = f"❌ Sorry, no {course} colleges found in '{district.title()}'. Try another district."

        await update.message.reply_text(reply, parse_mode='Markdown')
        context.user_data["awaiting_district"] = False

def prepare(raw, total):
    rank_map = {}
    for entry in raw:
        m = entry["m"]
        r = entry["r"]
        if m not in rank_map:
            rank_map[m] = []
        rank_map[m].append(r)

    rank_map[1] = [total]
    rank_map[0] = [total]
    marks = sorted(rank_map.keys(), reverse=True)
    return rank_map, marks

def avg(arr):
    return sum(arr) / len(arr)

def predict_rank(score, course):
    TOTAL = {
        "MCA": 18738,
        "MBA": 28875
    }
    raw = rawMCA if course.upper() == "MCA" else rawMBA
    total = TOTAL[course.upper()]
    rank_map, marks = prepare(raw, total)

    if score in rank_map:
        return round(avg(rank_map[score]))

    lower, upper = marks[-1], marks[0]
    for i in range(len(marks)):
        if marks[i] < score:
            upper = marks[i - 1]
            lower = marks[i]
            break

    r_low = avg(rank_map[lower])
    r_up = avg(rank_map[upper])
    rank = r_low + (score - lower) * (r_up - r_low) / (upper - lower)
    return round(rank)

# ✅ /predict
async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✍️ Please enter your details like this:\n\n`Name Course Marks`\n\nExample:\n`Arun MCA 54`", parse_mode="Markdown")
    context.user_data["awaiting_predict_input"] = True

# ✅ Rank prediction helper
def get_rank(marks: float, course: str):
    data = rawMCA if course.lower() == "mca" else rawMBA
    candidates = [d["r"] for d in data if d["m"] == int(marks)]
    if candidates:
        return round(sum(candidates) / len(candidates))
    data_sorted = sorted(data, key=lambda x: x["m"], reverse=True)
    for entry in data_sorted:
        if marks >= entry["m"]:
            return entry["r"]
    return data_sorted[-1]["r"]

# ✅ Handle prediction input
async def handle_predict_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_predict_input"):
        return

    text = update.message.text.strip()
    parts = text.split()

    if len(parts) < 3:
        await update.message.reply_text("⚠️ Format error. Use: `Name Course Marks` (e.g. `Arun MCA 54`)", parse_mode="Markdown")
        return

    name = " ".join(parts[:-2])
    course = parts[-2].upper()
    try:
        marks = float(parts[-1])
    except ValueError:
        await update.message.reply_text("⚠️ Marks must be a number (e.g. `54`)", parse_mode="Markdown")
        return

    if course not in ["MCA", "MBA"]:
        await update.message.reply_text("⚠️ Course must be either `MCA` or `MBA`.", parse_mode="Markdown")
        return

    user = update.effective_user
    user_id = user.id
    file_path = "pgcet_predict.csv"
    file_exists = os.path.isfile(file_path)
    rows = []

    # Read existing
    if file_exists:
        with open(file_path, "r", newline="") as file:
            reader = csv.reader(file)
            headers = next(reader, [])
            rows = list(reader)

    # Check if user already exists
    updated = False
    for i, row in enumerate(rows):
        if row and row[0] == str(user_id):
            rows[i] = [str(user_id), user.first_name, name, course, marks]
            updated = True
            break

    if not updated:
        rows.append([str(user_id), user.first_name, name, course, marks])

    # Write all data back
    with open(file_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["user_id", "telegram_name", "user_input_name", "course", "marks"])
        writer.writerows(rows)

    # Predict rank
    rank = predict_rank(marks, course)

    await update.message.reply_text(f"✅ *Saved!*\n\n👤 Name: {name}\n📚 Course: {course}\n📝 Marks: {marks}\n📈 Predicted Rank: *{rank}*", parse_mode="Markdown")
    context.user_data["awaiting_predict_input"] = False


# ✅ Text message handler
def is_user_input(update, context):
    return context.user_data.get("awaiting_predict_input") or context.user_data.get("awaiting_district")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_predict_input"):
        await handle_predict_input(update, context)
    elif context.user_data.get("awaiting_district"):
        await handle_district_input(update, context)


# ✅ Run the Bot
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("cutoffs", cutoffs))
app.add_handler(CommandHandler("mca_cutoff", mca_cutoff))
app.add_handler(CommandHandler("mba_cutoff", mba_cutoff))
app.add_handler(CommandHandler("syllabus", syllabus))
app.add_handler(CommandHandler("mca_syllabus", mca_syllabus))
app.add_handler(CommandHandler("mba_syllabus", mba_syllabus))
app.add_handler(CommandHandler("kea", kea))
app.add_handler(CommandHandler("colleges", colleges))
app.add_handler(CommandHandler("predict", predict))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🤖 PGCET Bot running...")
app.run_polling()
