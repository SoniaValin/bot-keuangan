from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)
import pandas as pd
from datetime import datetime
import os

# ===== TOKEN =====
TOKEN = os.getenv("BOT_TOKEN")

# ===== FOLDER =====
DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

current_file = os.path.join(DATA_FOLDER, "keuangan.xlsx")

# ===== INIT =====
def init_file(path):
    if not os.path.exists(path):
        df = pd.DataFrame(columns=["Tanggal","Jenis","Duit","Sisa","Keterangan"])
        df.to_excel(path, index=False)

init_file(current_file)

# ===== BASIC =====
def load_data():
    df = pd.read_excel(current_file)
    if not df.empty:
        df["Tanggal"] = pd.to_datetime(df["Tanggal"])
    return df

def save_data(df):
    df.to_excel(current_file, index=False)

def hitung_sisa(df):
    saldo = 0
    sisa = []
    for i in range(len(df)):
        if df.loc[i,"Jenis"] == "pemasukan":
            saldo += df.loc[i,"Duit"]
        else:
            saldo -= df.loc[i,"Duit"]
        sisa.append(saldo)
    df["Sisa"] = sisa
    return df

def parse_input(text):
    try:
        bagian = text.split()
        duit = int(bagian[0].replace(".", ""))
        ket = " ".join(bagian[1:])
        return duit, ket
    except:
        return None, None

# ===== STATE =====
INPUT_PEMASUKAN, INPUT_PENGELUARAN, KONFIRMASI, PILIH_FILE = range(4)

def reset_user(context):
    context.user_data.clear()

# ===== BATAL =====
async def batal(update, context):
    reset_user(context)
    await update.message.reply_text("Dibatalkan. Kembali ke /help")
    return ConversationHandler.END

# ===== PEMASUKAN =====
async def pemasukan_start(update, context):
    reset_user(context)
    context.user_data["jenis"] = "pemasukan"
    await update.message.reply_text("Format: 10000 gaji\n/batal untuk keluar")
    return INPUT_PEMASUKAN

async def pemasukan_input(update, context):
    duit, ket = parse_input(update.message.text)
    if duit is None:
        await update.message.reply_text("Format salah.")
        return INPUT_PEMASUKAN

    context.user_data["duit"] = duit
    context.user_data["ket"] = ket
    await update.message.reply_text(f"{duit} ({ket})\n/ya atau /tidak")
    return KONFIRMASI

# ===== PENGELUARAN =====
async def pengeluaran_start(update, context):
    reset_user(context)
    context.user_data["jenis"] = "pengeluaran"
    await update.message.reply_text("Format: 10000 makan\n/batal untuk keluar")
    return INPUT_PENGELUARAN

async def pengeluaran_input(update, context):
    duit, ket = parse_input(update.message.text)
    if duit is None:
        await update.message.reply_text("Format salah.")
        return INPUT_PENGELUARAN

    context.user_data["duit"] = duit
    context.user_data["ket"] = ket
    await update.message.reply_text(f"{duit} ({ket})\n/ya atau /tidak")
    return KONFIRMASI

# ===== KONFIRMASI =====
async def konfirmasi(update, context):
    text = update.message.text.lower()

    if text == "/ya":
        df = load_data()
        df.loc[len(df)] = [
            datetime.now(),
            context.user_data["jenis"],
            context.user_data["duit"],
            0,
            context.user_data["ket"]
        ]
        df = hitung_sisa(df)
        save_data(df)

        await update.message.reply_text("Tersimpan.")
        reset_user(context)
        return ConversationHandler.END

    elif text == "/tidak":
        await update.message.reply_text("Ulangi input.")
        if context.user_data["jenis"] == "pemasukan":
            return INPUT_PEMASUKAN
        return INPUT_PENGELUARAN

    return KONFIRMASI

# ===== RIWAYAT =====
async def riwayat(update, context):
    df = load_data()
    if df.empty:
        await update.message.reply_text("Belum ada data.")
        return

    teks = ""
    for i, row in df.tail(5).iterrows():
        teks += f"{row['Jenis']} | {row['Duit']} | {row['Keterangan']}\n"

    await update.message.reply_text(teks)

# ===== HAPUS TERAKHIR =====
async def hapus_terakhir(update, context):
    df = load_data()
    if df.empty:
        await update.message.reply_text("Tidak ada data.")
        return

    df = df.iloc[:-1]
    df = hitung_sisa(df)
    save_data(df)

    await update.message.reply_text("Transaksi terakhir dihapus.")

# ===== FILE =====
async def baru(update, context):
    nama = f"Keuangan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    path = os.path.join(DATA_FOLDER, nama)
    init_file(path)
    await update.message.reply_text(f"File: {nama}")

async def pilih(update, context):
    files = os.listdir(DATA_FOLDER)
    context.user_data["files"] = files

    teks = "\n".join([f"{i}. {f}" for i,f in enumerate(files)])
    await update.message.reply_text(teks)
    return PILIH_FILE

async def pilih_input(update, context):
    try:
        idx = int(update.message.text)
        context.user_data["selected"] = context.user_data["files"][idx]
        await update.message.reply_text("/gunakan atau /hapus_file")
    except:
        await update.message.reply_text("Salah.")
    return ConversationHandler.END

async def gunakan(update, context):
    global current_file
    file = context.user_data.get("selected")
    if not file:
        await update.message.reply_text("Belum pilih file.")
        return
    current_file = os.path.join(DATA_FOLDER, file)
    await update.message.reply_text(f"Pakai: {file}")

async def hapus_file(update, context):
    file = context.user_data.get("selected")
    if not file:
        await update.message.reply_text("Belum pilih file.")
        return
    os.remove(os.path.join(DATA_FOLDER, file))
    await update.message.reply_text("File dihapus.")

# ===== SISA =====
async def sisa(update, context):
    df = load_data()
    if df.empty:
        await update.message.reply_text("Belum ada data.")
        return
    await update.message.reply_text(f"Saldo: {df['Sisa'].iloc[-1]}")

# ===== HELP =====
async def help_command(update, context):
    await update.message.reply_text("""
COMMAND:
/pemasukan
/pengeluaran
/sisa
/riwayat
/hapus_terakhir

FILE:
/baru
/pilih
/gunakan
/hapus_file

LAINNYA:
/batal
/ya
/tidak
/help
""")

# ===== MAIN =====
app = ApplicationBuilder().token(TOKEN).build()

conv_pemasukan = ConversationHandler(
    entry_points=[CommandHandler("pemasukan", pemasukan_start)],
    states={
        INPUT_PEMASUKAN:[MessageHandler(filters.TEXT & ~filters.COMMAND, pemasukan_input)],
        KONFIRMASI:[MessageHandler(filters.TEXT & ~filters.COMMAND, konfirmasi)]
    },
    fallbacks=[CommandHandler("batal", batal)]
)

conv_pengeluaran = ConversationHandler(
    entry_points=[CommandHandler("pengeluaran", pengeluaran_start)],
    states={
        INPUT_PENGELUARAN:[MessageHandler(filters.TEXT & ~filters.COMMAND, pengeluaran_input)],
        KONFIRMASI:[MessageHandler(filters.TEXT & ~filters.COMMAND, konfirmasi)]
    },
    fallbacks=[CommandHandler("batal", batal)]
)

conv_pilih = ConversationHandler(
    entry_points=[CommandHandler("pilih", pilih)],
    states={
        PILIH_FILE:[MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_input)]
    },
    fallbacks=[CommandHandler("batal", batal)]
)

app.add_handler(conv_pemasukan)
app.add_handler(conv_pengeluaran)
app.add_handler(conv_pilih)

app.add_handler(CommandHandler("riwayat", riwayat))
app.add_handler(CommandHandler("hapus_terakhir", hapus_terakhir))
app.add_handler(CommandHandler("gunakan", gunakan))
app.add_handler(CommandHandler("hapus_file", hapus_file))
app.add_handler(CommandHandler("baru", baru))
app.add_handler(CommandHandler("sisa", sisa))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("batal", batal))

print("Bot jalan...")
app.run_polling()
