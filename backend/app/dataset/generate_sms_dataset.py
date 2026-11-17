#!/usr/bin/env python3
"""
Financial Coach - synthetic Egyptian bank-SMS dataset generator.

Produces one JSON file that can train BOTH models in the SMS pipeline:
  1. is_transaction  : transaction SMS vs. everything else (OTP, promo, declined, ...)
  2. category        : spending category for transaction SMS

Every row carries ground truth (amount, currency, merchant, datetime, ...) so the
same file also tests the regex/rule parser.

IMPORTANT - how honest the data is (see `template_origin` on every row):
  real                  copied from an SMS a real user received (only the BDC instant transfer)
  invented_from_real    same family as a real message, but the exact wording is a guess
  repo_mock             wording taken from Backend/Features/tests/samples.py (itself a guess)
  invented              plausible wording written for this dataset - MUST be checked against
                        real messages from that bank before you trust results on it

Splits (column `split`) are built to expose overfitting to the generator:
  train / validation          templates and merchants seen in training
  test_unseen_template        whole message templates never seen in training
  test_unseen_merchant        merchants / recipients never seen in training
Real messages live in a separate file and are never part of training.

Usage:  python generate_sms_dataset.py --out ./data --seed 42
"""
import argparse
import json
import math
import os
import random
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta

NOW = datetime(2026, 11, 15, 12, 0)
START = datetime(2025, 1, 1)

# --------------------------------------------------------------------------- #
# Normalisation (mirrors Backend/Features/sms_parser/patterns.py, + lowercase)
# --------------------------------------------------------------------------- #
_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ـ": None})
_DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_PUNCT = str.maketrans({"٫": ".", "٬": ",", "،": ",", "\u200f": None, "\u200e": None, "\u00a0": " "})
_DIAC = re.compile(r"[\u064B-\u065F\u0670]")
_AR_DIG = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def normalize(t: str) -> str:
    t = unicodedata.normalize("NFKC", t)
    t = t.translate(_DIG).translate(_PUNCT).translate(_FOLD)
    t = _DIAC.sub("", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def to_arabic_indic(s: str) -> str:
    s = re.sub(r"(?<=\d)\.(?=\d)", "٫", s)
    s = re.sub(r"(?<=\d),(?=\d)", "٬", s)
    return s.translate(_AR_DIG)


# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #
NAMED = {
    "Groceries": [("Carrefour", "كارفور"), ("Spinneys", "سبينيس"), ("Hyper One", "هايبر وان"),
                  ("Seoudi Market", "سعودي ماركت"), ("Metro Market", "مترو ماركت"), ("Kazyon", "كازيون"),
                  ("Fathalla Market", "فتح الله"), ("Gourmet Egypt", "جورميه"), ("Breadfast", "بريدفاست"),
                  ("InstaShop", "انستاشوب"), ("Awlad Ragab", "اولاد رجب"), ("Oscar Grand Stores", "اوسكار"),
                  ("Zahran Market", "زهران ماركت"), ("Alfa Market", "الفا ماركت"), ("Khair Zaman", "خير زمان"),
                  ("BIM Market", None), ("Lulu Hypermarket", "لولو هايبرماركت")],
    "Restaurants": [("McDonald's", "ماكدونالدز"), ("KFC", "كي اف سي"), ("Hardee's", "هارديز"),
                    ("Pizza Hut", "بيتزا هت"), ("Papa John's", "بابا جونز"), ("Domino's", "دومينوز"),
                    ("Cilantro", "سيلانترو"), ("Costa Coffee", "كوستا كوفي"), ("Starbucks", "ستاربكس"),
                    ("Tim Hortons", "تيم هورتنز"), ("Koshary Tahrir", "كشري التحرير"), ("Abou Tarek", "ابو طارق"),
                    ("Zooba", "زوبا"), ("Mo'men", "مؤمن"), ("Cook Door", "كوك دور"), ("Gad", "جاد"),
                    ("Tabali", "طبالي"), ("Texas Chicken", "تكساس تشيكن"), ("Elmenus", "المنيوس"),
                    ("Talabat", "طلبات"), ("Chili's", "تشيليز"), ("Dunkin'", "دانكن"),
                    ("Sobhy Kaber", "صبحي كابر"), ("El Abd Bakery", "العبد"), ("Mandarine Koueider", "ماندارين")],
    "Transportation": [("Uber", "اوبر"), ("Careem", "كريم"), ("inDrive", "اندرايف"), ("Swvl", "سويفل"),
                       ("DiDi", "ديدي"), ("Mobil", "موبيل"), ("TotalEnergies", "توتال"),
                       ("Misr Petroleum", "مصر للبترول"), ("Wataniya", "وطنية"), ("ChillOut", "تشيل اوت"),
                       ("Cairo Metro", "مترو الانفاق"), ("Egyptian National Railways", "السكة الحديد"),
                       ("TAQA Arabia", "طاقة عربية"), ("Ring Road Toll", "بوابة الدائري")],
    "Shopping": [("Amazon.eg", "امازون"), ("Noon", "نون"), ("Jumia", "جوميا"), ("B.TECH", "بي تك"),
                 ("Raya Shop", "راية شوب"), ("Dream 2000", "دريم 2000"), ("2B Egypt", "تو بي"), ("Zara", "زارا"),
                 ("H&M", "اتش اند ام"), ("DeFacto", "ديفاكتو"), ("LC Waikiki", "ال سي وايكيكي"),
                 ("IKEA", "ايكيا"), ("Decathlon", "ديكاتلون"), ("Elaraby Group", "العربي"),
                 ("Home Centre", "هوم سنتر"), ("Max Fashion", "ماكس"), ("Sprinter", "سبرنتر"),
                 ("Mango", "مانجو"), ("Adidas", "اديداس"), ("Nike", "نايكي")],
    "Utilities": [("Vodafone", "فودافون"), ("Orange", "اورانج"), ("e&", "اتصالات"), ("WE", "وي"),
                  ("Telecom Egypt", "المصرية للاتصالات"), ("Fawry", "فوري"),
                  ("North Cairo Electricity", "شمال القاهرة للكهرباء"),
                  ("South Cairo Electricity", "جنوب القاهرة للكهرباء"), ("Town Gas", "تاون جاس"),
                  ("Cairo Water Company", "مياه القاهرة"), ("Alexandria Water", "مياه الاسكندرية"),
                  ("TE Data", "تي اي داتا")],
    "Healthcare": [("Seif Pharmacies", "صيدليات سيف"), ("El Ezaby Pharmacy", "صيدليات العزبي"),
                   ("Misr Pharmacies", "صيدليات مصر"), ("Al Borg Laboratories", "معامل البرج"),
                   ("Cleopatra Hospital", "مستشفى كليوباترا"), ("Dar Al Fouad Hospital", "مستشفى دار الفؤاد"),
                   ("Vezeeta", "فيزيتا"), ("Cairo Scan", "كايرو سكان"), ("Alfa Lab", "معمل الفا"),
                   ("Rushdy Pharmacy", "صيدلية رشدي"), ("Care Pharmacy", "صيدلية كير")],
    "Entertainment": [("VOX Cinemas", "فوكس سينما"), ("Galaxy Cinema", "سينما جالاكسي"),
                      ("Dream Park", "دريم بارك"), ("PlayStation Store", "بلايستيشن"), ("Steam", None),
                      ("Xbox", None), ("Cairo Opera House", "دار الاوبرا"), ("Magic Planet", "ماجيك بلانيت"),
                      ("Egypt Bowling", "بولينج مصر"), ("Adrenaline Zone", "اڤرينالين")],
    "Subscription": [("Netflix", "نتفليكس"), ("Spotify", "سبوتيفاي"), ("Shahid VIP", "شاهد"),
                     ("Anghami", "انغامي"), ("YouTube Premium", "يوتيوب بريميوم"), ("Apple.com/Bill", "ابل"),
                     ("Google Play", "جوجل بلاي"), ("OpenAI ChatGPT", None), ("Microsoft 365", None),
                     ("Adobe", None), ("Canva", None), ("Disney Plus", "ديزني بلس"), ("Watch IT", "واتش ات")],
    "Education": [("American University in Cairo", "الجامعة الامريكية"),
                  ("German University in Cairo", "الجامعة الالمانية"), ("Nile University", "جامعة النيل"),
                  ("Udemy", None), ("Coursera", None), ("British Council", "المجلس الثقافي البريطاني"),
                  ("Cairo University", "جامعة القاهرة"), ("Future University", "جامعة المستقبل"),
                  ("Ain Shams University", "جامعة عين شمس"), ("Misr International University", "جامعة مصر الدولية"),
                  ("Nahdet Misr Books", "نهضة مصر")],
    "Travel": [("EgyptAir", "مصر للطيران"), ("Booking.com", None), ("Airbnb", None),
               ("Emirates", "طيران الامارات"), ("Qatar Airways", "الخطوط القطرية"), ("Air Cairo", "اير كايرو"),
               ("Hilton Hotels", "فنادق هيلتون"), ("Marriott", "ماريوت"), ("Sonesta Hotels", "فنادق سونستا"),
               ("Rixos Sharm", "ريكسوس شرم"), ("Almosafer", None)],
    "Personal Care": [("Gold's Gym", "جولدز جيم"), ("Sephora", "سيفورا"), ("Bath & Body Works", "باث اند بودي ووركس"),
                      ("Beauty Zone", "بيوتي زون"), ("The Body Shop", "ذا بودي شوب"), ("Mr. Barber", "مستر باربر"),
                      ("Platinum Gym", "بلاتينيوم جيم"), ("MAC Cosmetics", "ماك")],
}

PROC = {
    "Groceries": [("{n} Supermarket", "سوبر ماركت {n}"), ("{n} Market", "ماركت {n}"),
                  ("{n} Hypermarket", "هايبر {n}"), ("{n} Grocery", "بقالة {n}")],
    "Restaurants": [("{n} Restaurant", "مطعم {n}"), ("{n} Cafe", "كافيه {n}"), ("{n} Grill", "مشويات {n}"),
                    ("{n} Koshary", "كشري {n}"), ("{n} Pizza", "بيتزا {n}"), ("{n} Bakery", "مخبز {n}")],
    "Healthcare": [("{n} Pharmacy", "صيدلية {n}"), ("{n} Clinic", "عيادة {n}"),
                   ("{n} Hospital", "مستشفى {n}"), ("{n} Medical Lab", "معمل {n}")],
    "Education": [("{n} School", "مدرسة {n}"), ("{n} Academy", "اكاديمية {n}"),
                  ("{n} University", "جامعة {n}"), ("{n} Language Center", "مركز {n} للغات")],
    "Personal Care": [("{n} Salon", "صالون {n}"), ("{n} Barber", "حلاق {n}"), ("{n} Gym", "جيم {n}"),
                      ("{n} Spa", "سبا {n}")],
    "Travel": [("{n} Travel", "{n} للسياحة"), ("{n} Hotel", "فندق {n}"), ("{n} Resort", "منتجع {n}"),
               ("{n} Tours", "رحلات {n}")],
    "Shopping": [("{n} Store", "محل {n}"), ("{n} Fashion", "ملابس {n}"), ("{n} Electronics", "الكترونيات {n}"),
                 ("{n} Mobile", "موبايلات {n}"), ("{n} Shoes", "احذية {n}")],
    "Transportation": [("{n} Petrol Station", "محطة بنزين {n}"), ("{n} Parking", "موقف {n}"),
                       ("{n} Car Service", "خدمة سيارات {n}")],
    "Entertainment": [("{n} Cinema", "سينما {n}"), ("{n} Games", "العاب {n}"), ("{n} Club", "نادي {n}")],
}

NAMES = [("El Nour", "النور"), ("El Salam", "السلام"), ("El Amal", "الامل"), ("El Safwa", "الصفوة"),
         ("Hassan", "حسن"), ("Sherif", "شريف"), ("Abo Ali", "ابو علي"), ("El Fath", "الفتح"),
         ("Al Madina", "المدينة"), ("El Rahma", "الرحمة"), ("Zamalek", "الزمالك"), ("Maadi", "المعادي"),
         ("Nasr", "نصر"), ("Cairo", "القاهرة"), ("Delta", "الدلتا"), ("Nile", "النيل"),
         ("Pyramids", "الاهرام"), ("Alex", "اسكندرية"), ("El Shorouk", "الشروق"), ("El Tawheed", "التوحيد"),
         ("Ibn Sina", "ابن سينا"), ("El Baraka", "البركة"), ("El Khair", "الخير"), ("Salah", "صلاح"),
         ("Gamal", "جمال"), ("Mostafa", "مصطفى"), ("El Wafaa", "الوفاء"), ("El Horreya", "الحرية"),
         ("El Fardous", "الفردوس"), ("Mansoura", "المنصورة"), ("Tanta", "طنطا"), ("El Sayed", "السيد"),
         ("Mahmoud", "محمود"), ("Fathy", "فتحي"), ("Saad", "سعد"), ("Nabil", "نبيل"), ("Kareem", "كريم"),
         ("Yasmin", "ياسمين"), ("Lotus", "لوتس"), ("Sphinx", "سفنكس")]

FIRST = [("Ahmed", "احمد"), ("Mohamed", "محمد"), ("Mahmoud", "محمود"), ("Omar", "عمر"), ("Youssef", "يوسف"),
         ("Mostafa", "مصطفى"), ("Hassan", "حسن"), ("Karim", "كريم"), ("Sara", "سارة"), ("Nour", "نور"),
         ("Mariam", "مريم"), ("Hoda", "هدي"), ("Amr", "عمرو"), ("Khaled", "خالد"), ("Rania", "رانيا"),
         ("Eman", "ايمان"), ("Tamer", "تامر"), ("Dina", "دينا"), ("Ali", "علي"), ("Mona", "منى")]
LAST = [("Khalil", "خليل"), ("Hassan", "حسن"), ("Ali", "علي"), ("Sherif", "شريف"), ("Adel", "عادل"),
        ("Samy", "سامي"), ("Ibrahim", "ابراهيم"), ("Nabil", "نبيل"), ("Fathy", "فتحي"), ("Salah", "صلاح"),
        ("Samir", "سمير"), ("Gamal", "جمال"), ("Wael", "وائل"), ("Essam", "عصام"), ("Hamdy", "حمدي"),
        ("Said", "سعيد"), ("Tarek", "طارق"), ("Mahmoud", "محمود")]

LOCS = [("MAADI", "المعادي"), ("NASR CITY", "مدينة نصر"), ("ZAMALEK", "الزمالك"), ("MOHANDESSIN", "المهندسين"),
        ("HELIOPOLIS", "مصر الجديدة"), ("DOKKI", "الدقي"), ("NEW CAIRO", "القاهرة الجديدة"),
        ("6TH OCTOBER", "6 اكتوبر"), ("SHEIKH ZAYED", "الشيخ زايد"), ("ALEXANDRIA", "الاسكندرية"),
        ("GIZA", "الجيزة"), ("TAGAMOA", "التجمع"), ("MALL OF EGYPT", "مول مصر"), ("CAIRO FESTIVAL CITY", "كايرو فستيفال")]

FEES_EN = ["monthly card maintenance", "SMS notification service", "ATM withdrawal at another bank",
           "account maintenance", "card replacement", "instant transfer", "annual card fee"]
FEES_AR = ["رسوم صيانة البطاقة", "رسوم خدمة الرسائل", "رسوم السحب من ماكينة بنك اخر",
           "مصاريف ادارية", "رسوم اصدار بدل فاقد", "رسوم تحويل لحظي", "الرسوم السنوية للبطاقة"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]

POS = ["Groceries", "Restaurants", "Transportation", "Shopping", "Utilities", "Healthcare",
       "Entertainment", "Subscription", "Education", "Travel", "Personal Care"]
ECOM = ["Shopping", "Subscription", "Entertainment", "Education", "Travel", "Transportation",
        "Restaurants", "Groceries", "Healthcare"]
ALL_CATEGORIES = POS + ["Transfer", "Income", "Cash Withdrawal", "Fees", "Refund"]

AMT = {"Groceries": (40, 3000), "Restaurants": (30, 1500), "Transportation": (20, 800),
       "Shopping": (100, 15000), "Utilities": (50, 2500), "Healthcare": (30, 5000),
       "Entertainment": (50, 1500), "Subscription": (40, 700), "Education": (500, 40000),
       "Travel": (500, 30000), "Personal Care": (50, 2500), "Transfer": (20, 20000),
       "Income": (3000, 40000), "Cash Withdrawal": (100, 5000), "Fees": (1, 150), "Refund": (20, 3000)}

BANKS = ["CIB", "NBE", "BANQUE_MISR", "QNB", "BANQUE_DU_CAIRE"]
SENDERS = {"CIB": ["CIB"], "NBE": ["NBE"], "BANQUE_MISR": ["BANQUE MISR"], "QNB": ["QNB"],
           "BANQUE_DU_CAIRE": ["BDC"]}


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #
def T(id, bank, lang, kind, typ, direction, cats, text, merchant=None, datefmt="auto", cur_style=None,
      amtfmt="auto", origin="invented", fx=False, digits=None, no_holdout=False, amt_range=None):
    return dict(id=id, bank=bank, lang=lang, kind=kind, type=typ, direction=direction, cats=cats, text=text,
                merchant=merchant, datefmt=datefmt, cur_style=cur_style or ("en" if lang == "en" else "mixed"),
                amtfmt=amtfmt, origin=origin, fx=fx, digits=(lang == "ar") if digits is None else digits,
                no_holdout=no_holdout, amt_range=amt_range)


def build_templates():
    t = []
    A = t.append
    R, I = "repo_mock", "invented"

    # ---------------- transactions: CIB ----------------
    A(T("cib_purchase", "CIB", "en", "txn", "purchase", "debit", POS,
        "Purchase of {cur} {amt} at {merchant} on {date} {time}. Card ending {card4}", "pos", origin=R))
    A(T("cib_purchase_txn", "CIB", "en", "txn", "purchase", "debit", POS,
        "Your card ending {card4} was used for a purchase transaction of {cur} {amt} at {merchant} on {date}. "
        "Available balance {cur} {bal}", "pos", origin=I))
    A(T("cib_purchase_short", "CIB", "en", "txn", "purchase", "debit", POS,
        "CIB: {cur} {amt} spent at {merchant} on {date} {time}", "pos", origin=I))
    A(T("cib_ecom", "CIB", "en", "txn", "ecom_purchase", "debit", ECOM,
        "Online purchase of {cur} {amt} at {merchant} using card ending {card4} on {date}", "pos", fx=True, origin=I))
    A(T("cib_transfer_out", "CIB", "en", "txn", "transfer_out", "debit", ["Transfer"],
        "Transfer of {cur} {amt} to {recipient} on {date}", "recipient", origin=R))
    A(T("cib_transfer_in", "CIB", "en", "txn", "transfer_in", "credit", ["Transfer"],
        "You have received a transfer of {cur} {amt} from {recipient}", "recipient", origin=R))
    A(T("cib_atm", "CIB", "en", "txn", "atm_withdrawal", "debit", ["Cash Withdrawal"],
        "{cur} {amt} has been withdrawn from your account at ATM {atm}", "atm", origin=R))
    A(T("cib_credit", "CIB", "en", "txn", "deposit", "credit", ["Income"],
        "{cur} {amt} has been credited to your account", origin=R))
    A(T("cib_salary", "CIB", "en", "txn", "salary", "credit", ["Income"],
        "Salary of {cur} {amt} has been credited to your account ending {acct4} on {date}", origin=I))
    A(T("cib_fee", "CIB", "en", "txn", "fee", "debit", ["Fees"],
        "A fee of {cur} {amt} has been charged to your account for {fee}", origin=I))
    A(T("cib_refund", "CIB", "en", "txn", "refund", "credit", ["Refund"],
        "Refund of {cur} {amt} from {merchant} has been credited to your card ending {card4}", "pos", origin=I))
    A(T("cib_bill", "CIB", "en", "txn", "bill_payment", "debit", ["Utilities"],
        "Bill payment of {cur} {amt} to {merchant} was successful. Ref {txid}", "bill", origin=I))

    # ---------------- transactions: NBE ----------------
    A(T("nbe_purchase_ar", "NBE", "ar", "txn", "purchase", "debit", POS,
        "خصم مبلغ {amt} {cur} لشراء لدى {merchant} بتاريخ {date}", "pos", origin=R))
    A(T("nbe_purchase_ar_prefix", "NBE", "ar", "txn", "purchase", "debit", POS,
        "خصم مبلغ {cur} {amt} لشراء لدى {merchant} بتاريخ {date}", "pos", cur_style="en", origin=R))
    A(T("nbe_purchase_en", "NBE", "en", "txn", "purchase", "debit", POS,
        "Purchase of {cur} {amt} at {merchant} on {date} {time}", "pos", origin=R))
    A(T("nbe_purchase_card_ar", "NBE", "ar", "txn", "purchase", "debit", POS,
        "تم خصم {amt} {cur} من بطاقتكم المنتهية بـ {card4} عن عملية شراء من {merchant} في {date} {time}. "
        "الرصيد المتاح {bal} {cur}", "pos", origin=I))
    A(T("nbe_atm_ar", "NBE", "ar", "txn", "atm_withdrawal", "debit", ["Cash Withdrawal"],
        "سحب نقدي مبلغ {amt} {cur} من ماكينة {atm} بتاريخ {date}", "atm", origin=R))
    A(T("nbe_transfer_out_ar", "NBE", "ar", "txn", "transfer_out", "debit", ["Transfer"],
        "تم تحويل مبلغ {amt} {cur} الي {recipient} بتاريخ {date}", "recipient", origin=I))
    A(T("nbe_transfer_in_ar", "NBE", "ar", "txn", "transfer_in", "credit", ["Transfer"],
        "تم استلام تحويل بمبلغ {amt} {cur} من {recipient} في {date}", "recipient", origin=I))
    A(T("nbe_credit_ar", "NBE", "ar", "txn", "deposit", "credit", ["Income"],
        "تم اضافة مبلغ {amt} {cur} الي حسابكم بتاريخ {date}", origin=I))
    A(T("nbe_salary_ar", "NBE", "ar", "txn", "salary", "credit", ["Income"],
        "تم ايداع مرتبكم بمبلغ {amt} {cur} في حسابكم رقم {acct4}", origin=I))
    A(T("nbe_fee_ar", "NBE", "ar", "txn", "fee", "debit", ["Fees"],
        "تم خصم {amt} {cur} من حسابكم مقابل {fee}", origin=I))
    A(T("nbe_refund_ar", "NBE", "ar", "txn", "refund", "credit", ["Refund"],
        "تم رد مبلغ {amt} {cur} من {merchant} الي بطاقتكم المنتهية بـ {card4}", "pos", origin=I))
    A(T("nbe_bill_ar", "NBE", "ar", "txn", "bill_payment", "debit", ["Utilities"],
        "تم سداد فاتورة {merchant} بمبلغ {amt} {cur} بنجاح", "bill", origin=I))

    # ---------------- transactions: Banque Misr ----------------
    A(T("bm_charged", "BANQUE_MISR", "en", "txn", "purchase", "debit", POS,
        "charged {amt} {cur} at {merchant}", "pos", origin=R))
    A(T("bm_charged_full", "BANQUE_MISR", "en", "txn", "purchase", "debit", POS,
        "Banque Misr: your card ending {card4} was charged {amt} {cur} at {merchant} on {date} {time}", "pos", origin=I))
    A(T("bm_ecom_en", "BANQUE_MISR", "en", "txn", "ecom_purchase", "debit", ECOM,
        "Online payment of {amt} {cur} to {merchant} approved for card ending {card4}", "pos", fx=True, origin=I))
    A(T("bm_atm_ar", "BANQUE_MISR", "ar", "txn", "atm_withdrawal", "debit", ["Cash Withdrawal"],
        "سحب مبلغ {amt} {cur} من ماكينة {atm}", "atm", origin=R))
    A(T("bm_transfer_ar", "BANQUE_MISR", "ar", "txn", "transfer_out", "debit", ["Transfer"],
        "تحويل مبلغ {amt} {cur} الي {recipient}", "recipient", origin=R))
    A(T("bm_instapay_out_ar", "BANQUE_MISR", "ar", "txn", "transfer_out", "debit", ["Transfer"],
        "تم تحويل مبلغ {amt} {cur} عبر انستاباي الي {recipient} رقم المرجع {txid}", "recipient", origin=I))
    A(T("bm_instapay_in_ar", "BANQUE_MISR", "ar", "txn", "transfer_in", "credit", ["Transfer"],
        "تم استلام مبلغ {amt} {cur} عبر انستاباي من {recipient}", "recipient", origin=I))
    A(T("bm_bill_ar", "BANQUE_MISR", "ar", "txn", "bill_payment", "debit", ["Utilities"],
        "تم دفع فاتورة {merchant} بمبلغ {amt} {cur} بنجاح", "bill", origin=I))
    A(T("bm_salary_en", "BANQUE_MISR", "en", "txn", "salary", "credit", ["Income"],
        "Your salary of {amt} {cur} has been deposited on {date}", origin=I))
    A(T("bm_fee_ar", "BANQUE_MISR", "ar", "txn", "fee", "debit", ["Fees"],
        "تم خصم رسوم {fee} بمبلغ {amt} {cur}", origin=I))

    # ---------------- transactions: QNB ----------------
    A(T("qnb_purchase_en", "QNB", "en", "txn", "purchase", "debit", POS,
        "QNB: Purchase of {cur} {amt} at {merchant}, card ending {card4}. {date} {time}", "pos", origin=I))
    A(T("qnb_purchase_ar", "QNB", "ar", "txn", "purchase", "debit", POS,
        "بنك قطر الوطني: تمت عملية شراء بمبلغ {amt} {cur} لدى {merchant} بالبطاقة المنتهية بـ {card4}", "pos", origin=I))
    A(T("qnb_ecom_en", "QNB", "en", "txn", "ecom_purchase", "debit", ECOM,
        "QNB: Online transaction of {cur} {amt} at {merchant} on {date}. Card ending {card4}", "pos", fx=True, origin=I))
    A(T("qnb_atm_en", "QNB", "en", "txn", "atm_withdrawal", "debit", ["Cash Withdrawal"],
        "QNB: {cur} {amt} withdrawn from ATM {atm} on {date} {time}", "atm", origin=I))
    A(T("qnb_transfer_out_en", "QNB", "en", "txn", "transfer_out", "debit", ["Transfer"],
        "QNB: You have transferred {cur} {amt} to {recipient} on {date}", "recipient", origin=I))
    A(T("qnb_credit_en", "QNB", "en", "txn", "deposit", "credit", ["Income"],
        "QNB: {cur} {amt} credited to your account ending {acct4} on {date}", origin=I))
    A(T("qnb_fee_en", "QNB", "en", "txn", "fee", "debit", ["Fees"],
        "QNB: {cur} {amt} fee charged to your account for {fee}", origin=I))
    A(T("qnb_refund_en", "QNB", "en", "txn", "refund", "credit", ["Refund"],
        "QNB: Refund of {cur} {amt} from {merchant} credited to card ending {card4}", "pos", origin=I))

    # ---------------- transactions: Banque du Caire (BDC) ----------------
    # Wording copied from two real SMS (Nov 2026). Date order is MM/DD/YY (verified against the
    # phone's own timestamps). Recipient is NOT in the message, hence no counterparty.
    A(T("bdc_instant_transfer_out", "BANQUE_DU_CAIRE", "ar", "txn", "transfer_out", "debit", ["Transfer"],
        "تم تنفيذ تحويل لحظي من حسابكم {acct4} بمبلغ {amt} جم في {time} يوم {date} "
        "رقم المعاملة {txid} للمزيد أتصل ب 16990",
        datefmt="mdy2", amtfmt="plain2", digits=False, origin="real", no_holdout=True))
    A(T("bdc_instant_transfer_in", "BANQUE_DU_CAIRE", "ar", "txn", "transfer_in", "credit", ["Transfer"],
        "تم استلام تحويل لحظي في حسابكم {acct4} بمبلغ {amt} جم في {time} يوم {date} "
        "رقم المعاملة {txid} للمزيد أتصل ب 16990",
        datefmt="mdy2", amtfmt="plain2", digits=False, origin="invented_from_real", no_holdout=True))

    # ---------------- NOT transactions ----------------
    # OTP
    A(T("otp_en_1", "ANY", "en", "neg", "otp", None, [], "Your OTP is {otp} - do not share it with anyone", origin=R))
    A(T("otp_ar_1", "ANY", "ar", "neg", "otp", None, [], "رمز التحقق الخاص بك هو {otp}. لا تشاركه مع احد", origin=I))
    A(T("otp_en_login", "ANY", "en", "neg", "otp", None, [],
        "Use code {otp} to log in to your mobile banking. It expires in 5 minutes", origin=I))
    A(T("otp_en_purchase", "ANY", "en", "neg", "otp", None, [],
        "{otp} is your one-time password for your online purchase of {cur} {amt} at {merchant}. "
        "Do not share it with anyone", "pos", origin=I))
    A(T("otp_ar_purchase", "ANY", "ar", "neg", "otp", None, [],
        "كود التحقق {otp} لاتمام عملية الدفع بمبلغ {amt} {cur} لدى {merchant}. لا تشاركه مع احد", "pos", origin=I))
    # balance
    A(T("bal_en_1", "ANY", "en", "neg", "balance_alert", None, [],
        "Available balance {cur} {bal} as of {date}", origin=R))
    A(T("bal_ar_1", "ANY", "ar", "neg", "balance_alert", None, [],
        "رصيدكم المتاح {bal} {cur} في {date}", origin=I))
    A(T("bal_en_2", "ANY", "en", "neg", "balance_alert", None, [],
        "Your account ending {acct4} has a balance of {cur} {bal} as of {date} {time}", origin=I))
    A(T("bal_ar_low", "ANY", "ar", "neg", "balance_alert", None, [],
        "تنبيه: رصيد حسابكم المنتهي بـ {acct4} اقل من {amt} {cur}", amt_range=(100, 2000), origin=I))
    # declined / failed
    A(T("dec_en_1", "ANY", "en", "neg", "declined", None, [],
        "Transaction declined due to insufficient funds", origin=R))
    A(T("dec_en_2", "ANY", "en", "neg", "declined", None, [],
        "Your card ending {card4} purchase of {cur} {amt} at {merchant} was declined. Reason: insufficient funds",
        "pos", origin=I))
    A(T("dec_ar_1", "ANY", "ar", "neg", "declined", None, [],
        "تم رفض عملية الشراء بمبلغ {amt} {cur} لدى {merchant} لعدم كفاية الرصيد", "pos", origin=I))
    A(T("dec_ar_2", "ANY", "ar", "neg", "declined", None, [],
        "فشلت عملية التحويل بمبلغ {amt} {cur}. برجاء المحاولة لاحقا", origin=I))
    A(T("dec_en_atm", "ANY", "en", "neg", "declined", None, [],
        "ATM withdrawal of {cur} {amt} failed. Please try again later", origin=I))
    # promo
    A(T("promo_en_cashback", "ANY", "en", "neg", "promo", None, [],
        "Enjoy {pct}% cashback at {merchant} with your card. Spend up to {cur} {amt}. Valid until {date}. "
        "T&Cs apply", "pos", amt_range=(300, 5000), origin=I))
    A(T("promo_ar_discount", "ANY", "ar", "neg", "promo", None, [],
        "احصل علي خصم {pct}% لدى {merchant} باستخدام بطاقتكم حتي {date}", "pos", origin=I))
    A(T("promo_en_loan", "ANY", "en", "neg", "promo", None, [],
        "Need cash? Get a personal loan up to {cur} {amt} with no admin fees. Call {hotline}",
        amt_range=(20000, 300000), origin=I))
    A(T("promo_ar_loan", "ANY", "ar", "neg", "promo", None, [],
        "قرض شخصي حتي {amt} {cur} بدون مصاريف ادارية. للاستفسار اتصل {hotline}",
        amt_range=(20000, 300000), origin=I))
    A(T("promo_en_installment", "ANY", "en", "neg", "promo", None, [],
        "0% installments up to 24 months at {merchant} with your credit card. Visit your nearest branch",
        "pos", origin=I))
    A(T("promo_telecom_ar", "TELECOM", "ar", "neg", "promo", None, [],
        "عرض خاص: {amt} {cur} فقط للحصول علي باقة انترنت {gb} جيجا. للاشتراك اطلب {ussd}",
        amt_range=(30, 400), origin=I))
    # bill reminders (not paid yet)
    A(T("billrem_en_1", "ANY", "en", "neg", "bill_reminder", None, [],
        "Your {merchant} bill of {cur} {amt} is due on {date}. Pay now via the mobile app", "bill", origin=I))
    A(T("billrem_ar_1", "ANY", "ar", "neg", "bill_reminder", None, [],
        "فاتورة {merchant} المستحقة بمبلغ {amt} {cur} تستحق السداد في {date}", "bill", origin=I))
    A(T("billrem_en_cc", "ANY", "en", "neg", "bill_reminder", None, [],
        "Your credit card statement is ready. Minimum due {cur} {amt} by {date}", amt_range=(100, 3000), origin=I))
    A(T("billrem_ar_cc", "ANY", "ar", "neg", "bill_reminder", None, [],
        "كشف حساب بطاقة الائتمان جاهز. الحد الادني المستحق {amt} {cur} قبل {date}",
        amt_range=(100, 3000), origin=I))
    # security
    A(T("sec_en_login", "ANY", "en", "neg", "security_alert", None, [],
        "New login to your mobile banking from a new device. If this wasn't you, call {hotline}", origin=I))
    A(T("sec_ar_login", "ANY", "ar", "neg", "security_alert", None, [],
        "تم تسجيل الدخول الي حسابكم من جهاز جديد. اذا لم تكن انت اتصل ب {hotline}", origin=I))
    A(T("sec_en_pwd", "ANY", "en", "neg", "security_alert", None, [],
        "Your mobile banking password was changed successfully on {date}", origin=I))
    A(T("sec_ar_limit", "ANY", "ar", "neg", "security_alert", None, [],
        "تم تغيير حد السحب اليومي لبطاقتكم المنتهية بـ {card4}", origin=I))
    # phishing (sender is a plain phone number)
    A(T("phish_en_1", "PHONE", "en", "neg", "phishing", None, [],
        "Your account has been suspended. Verify your identity now: {url}", digits=False, origin=I))
    A(T("phish_ar_1", "PHONE", "ar", "neg", "phishing", None, [],
        "تم ايقاف بطاقتكم. لتفعيلها اضغط علي الرابط {url}", digits=False, origin=I))
    A(T("phish_en_prize", "PHONE", "en", "neg", "phishing", None, [],
        "Congratulations! You won {cur} {amt}. Claim now: {url}", amt_range=(5000, 100000), digits=False, origin=I))
    A(T("phish_ar_prize", "PHONE", "ar", "neg", "phishing", None, [],
        "مبروك لقد ربحت {amt} {cur}. اضغط للاستلام {url}", amt_range=(5000, 100000), digits=False, origin=I))
    # service info
    A(T("info_en_stmt", "ANY", "en", "neg", "service_info", None, [],
        "Your e-statement for {month} is now available in the mobile app", origin=I))
    A(T("info_en_card", "ANY", "en", "neg", "service_info", None, [],
        "Your card ending {card4} has been activated successfully", origin=I))
    A(T("info_ar_card", "ANY", "ar", "neg", "service_info", None, [],
        "تم تفعيل بطاقتكم المنتهية بـ {card4} بنجاح", origin=I))
    A(T("info_en_req", "ANY", "en", "neg", "service_info", None, [],
        "Your request has been received. Reference number {txid}. We will contact you within 3 working days",
        origin=I))
    A(T("info_ar_req", "ANY", "ar", "neg", "service_info", None, [],
        "تم استلام طلبكم رقم {txid}. سيتم التواصل معكم خلال 3 ايام عمل", origin=I))
    A(T("info_en_call", "ANY", "en", "neg", "service_info", None, [],
        "For inquiries call our customer service on {hotline}", origin=I))
    return t


# --------------------------------------------------------------------------- #
# Slot fillers
# --------------------------------------------------------------------------- #
def decorate(s, is_ar, rng):
    if is_ar:
        return s + " " + rng.choice(LOCS)[1] if rng.random() < 0.25 else s
    if rng.random() < 0.6:
        s = s.upper()
    if rng.random() < 0.30:
        loc = rng.choice(LOCS)[0]
        s += " " + (loc if s.isupper() else loc.title())
    if rng.random() < 0.10:
        s += f" {rng.randint(1000, 9999)}"
    if rng.random() < 0.15:
        s += " " + rng.choice(["EG", "EGY", "CAIRO EG"] if s.isupper() else ["EG", "Cairo EG"])
    return s


def pick_merchant(cat, lang, rng):
    named, proc = NAMED.get(cat, []), PROC.get(cat)
    if named and (not proc or rng.random() < 0.65):
        en, ar = rng.choice(named)
        base = f"named:{cat}:{en}"
    else:
        n_en, n_ar = rng.choice(NAMES)
        p_en, p_ar = rng.choice(proc)
        en, ar, base = p_en.format(n=n_en), p_ar.format(n=n_ar), f"proc:{n_en}"
    use_ar = lang == "ar" and ar is not None and rng.random() < 0.6
    return dict(text=decorate(ar if use_ar else en, use_ar, rng), canon=en, base=base)


def pick_bill_merchant(lang, rng):
    en, ar = rng.choice(NAMED["Utilities"])
    use_ar = lang == "ar" and ar is not None and rng.random() < 0.7
    return dict(text=ar if use_ar else en, canon=en, base=f"named:Utilities:{en}")


def pick_person(lang, rng):
    f, l = rng.choice(FIRST), rng.choice(LAST)
    if lang == "ar" and rng.random() < 0.8:
        return f"{f[1]} {l[1]}"
    s = f"{f[0]} {l[0]}"
    return s.upper() if rng.random() < 0.4 else s


def pick_atm(lang, rng):
    en, ar = rng.choice(LOCS)
    return ar if lang == "ar" and rng.random() < 0.7 else en


def rand_amount(lo, hi, rng, cat=None):
    v = max(math.exp(rng.uniform(math.log(lo), math.log(hi))), 1.0)
    if cat == "Cash Withdrawal":
        return float(max(100, round(v / 50) * 50))
    r = rng.random()
    if r < 0.25:
        return float(max(1, round(v)))
    if r < 0.45:
        return float(max(5, round(v / 5) * 5))
    return round(v, 2)


def fmt_amount(v, style, rng):
    if style == "auto":
        style = rng.choice(["plain2", "comma2", "comma2", "int"])
    if style == "int" and v != int(v):
        style = "comma2"
    if style == "int":
        return str(int(v))
    return f"{v:,.2f}" if style == "comma2" else f"{v:.2f}"


def cur_token(style, rng):
    if style == "mixed":
        style = "en" if rng.random() < 0.25 else "ar"
    if style == "en":
        return rng.choices(["EGP", "LE", "L.E.", "E£"], [75, 10, 5, 10])[0]
    return rng.choices(["جنيه", "جم", "ج.م", "جنيه مصري"], [40, 25, 10, 25])[0]


def fmt_date(dt, style, rng):
    if style == "auto":
        style = rng.choices(["dmy4", "iso", "dmon"], [65, 15, 20])[0]
    if style == "mdy2":
        return f"{dt.month}/{dt.day}/{dt.year % 100}"
    if style == "iso":
        return dt.strftime("%Y-%m-%d")
    if style == "dmon":
        return dt.strftime("%d-%b-%Y")
    return f"{dt.day:02d}/{dt.month:02d}/{dt.year}" if rng.random() < 0.7 else f"{dt.day}/{dt.month}/{dt.year}"


def fmt_time(dt, bdc, rng):
    if bdc:
        return dt.strftime("%H:%M")
    style = rng.choices(["hm", "hms", "h12"], [70, 20, 10])[0]
    if style == "hms":
        return dt.strftime("%H:%M:%S")
    if style == "h12":
        return dt.strftime("%I:%M %p").lstrip("0")
    return dt.strftime("%H:%M")


def rand_dt(rng):
    span = int((NOW - START).total_seconds())
    d = START + timedelta(seconds=rng.randint(0, span))
    return d.replace(hour=rng.randint(7, 23), minute=rng.randint(0, 59), second=rng.randint(0, 59))


def add_noise(text, lang, rng):
    tags = []
    if lang == "en" and rng.random() < 0.05:
        text = text.upper()
        tags.append("upper")
    if lang == "ar":
        for pat, rep, tag, p in [("[أإآ]", "ا", "alef_fold", 0.25), ("ى", "ي", "yaa_fold", 0.10),
                                 ("ة", "ه", "taa_marbuta", 0.08)]:
            if rng.random() < p:
                new = re.sub(pat, rep, text)
                if new != text:
                    text = new
                    tags.append(tag)
    if rng.random() < 0.05:
        text = re.sub(" ", lambda m: "  " if rng.random() < 0.15 else " ", text)
        tags.append("extra_space")
    if text.endswith(".") and rng.random() < 0.10:
        text = text[:-1]
        tags.append("no_final_period")
    return text, tags


# --------------------------------------------------------------------------- #
# One message
# --------------------------------------------------------------------------- #
def realize(t, rng, cat=None):
    lang = t["lang"]
    cat = cat if cat is not None else None
    bank = t["bank"]
    if bank == "ANY":
        bank = rng.choice(BANKS)
    sender_type = "bank"
    if bank == "TELECOM":
        sender, bank, sender_type = rng.choice(["Vodafone", "Orange", "WE", "Etisalat"]), "UNKNOWN", "telecom"
    elif bank == "PHONE":
        sender, bank, sender_type = "+2010" + "".join(rng.choices("0123456789", k=8)), "UNKNOWN", "phone_number"
    else:
        sender = rng.choice(SENDERS[bank])

    # money
    fx = t["fx"] and rng.random() < 0.45
    if fx:
        v = round(math.exp(rng.uniform(math.log(2), math.log(150))), 2)
        currency = cur_str = rng.choice(["USD", "USD", "USD", "EUR"])
        amt_str = fmt_amount(v, "plain2", rng)
    else:
        if t["amt_range"]:
            lo, hi = t["amt_range"]
            v = rand_amount(lo, hi, rng)
        elif cat:
            v = rand_amount(*AMT[cat], rng, cat=cat)
        else:
            v = rand_amount(30, 5000, rng)
        currency = "EGP"
        cur_str = cur_token(t["cur_style"], rng)
        amt_str = fmt_amount(v, t["amtfmt"], rng)
    bal = fmt_amount(float(rng.randint(100, 250000)), "comma2", rng)

    # merchant / counterparty
    rec = dict(merchant=None, merchant_text=None, counterparty_text=None, _base=None)
    s = {}
    mtype = t["merchant"]
    if mtype == "pos":
        mcat = cat if cat in NAMED else rng.choice(ECOM if t["fx"] else POS)
        m = pick_merchant(mcat, lang, rng)
        s["merchant"] = m["text"]
        rec.update(merchant=m["canon"], merchant_text=m["text"], _base=m["base"])
    elif mtype == "bill":
        m = pick_bill_merchant(lang, rng)
        s["merchant"] = m["text"]
        rec.update(merchant=m["canon"], merchant_text=m["text"], _base=m["base"])
    elif mtype == "recipient":
        s["recipient"] = pick_person(lang, rng)
        rec["counterparty_text"] = s["recipient"]
    elif mtype == "atm":
        s["atm"] = pick_atm(lang, rng)
        rec.update(merchant="ATM", merchant_text=s["atm"])

    dt = rand_dt(rng)
    has_date, has_time = "{date}" in t["text"], "{time}" in t["text"]
    bdc = t["bank"] == "BANQUE_DU_CAIRE"
    hexid = "".join(rng.choices("0123456789abcdef", k=8)) if bdc else "".join(rng.choices("0123456789", k=9))
    card4, acct4 = f"{rng.randint(0, 9999):04d}", f"{rng.randint(0, 9999):04d}"
    s.update(
        amt=amt_str, cur=cur_str, bal=bal, card4=card4, acct4=acct4, txid=hexid,
        date=fmt_date(dt, t["datefmt"], rng), time=fmt_time(dt, bdc, rng),
        otp="".join(rng.choices("0123456789", k=rng.choice([4, 5, 6]))),
        pct=rng.choice([5, 10, 15, 20, 25, 30, 50]),
        hotline=rng.choice(["16", "19", "15"]) + "".join(rng.choices("0123456789", k=3)),
        url=rng.choice(["http://bit.ly/", "https://tinyurl.com/", "http://cutt.ly/"])
            + "".join(rng.choices("abcdefghijkmnpqrstuvwxyz23456789", k=6)),
        gb=rng.choice([5, 10, 20, 40, 100]), ussd=f"*{rng.randint(100, 999)}#",
        month=rng.choice(MONTHS), fee=rng.choice(FEES_AR if lang == "ar" else FEES_EN),
    )
    text = t["text"].format(**s)
    if t["digits"] and lang == "ar" and rng.random() < 0.12:
        text = to_arabic_indic(text)
        noise = ["arabic_indic_digits"]
    else:
        noise = []
    if t["origin"] != "real":  # bank systems do not make typos; noise only for robustness
        text, tags = add_noise(text, lang, rng)
        noise += tags

    is_txn = t["kind"] == "txn"
    if has_date:
        dt_local = dt.strftime("%Y-%m-%dT%H:%M:%S") if has_time else dt.strftime("%Y-%m-%d")
    else:
        dt_local = None
    return {
        "sender": sender, "sender_type": sender_type, "text": text, "text_norm": normalize(text),
        "language": lang, "bank": bank, "is_transaction": is_txn,
        "type": t["type"], "direction": t["direction"], "category": cat if is_txn else None,
        "amount": v if is_txn else None, "currency": currency if is_txn else None,
        "mentions_amount": "{amt}" in t["text"] or "{bal}" in t["text"],
        "merchant": rec["merchant"] if is_txn else None,
        "merchant_text": rec["merchant_text"] if is_txn else None,
        "counterparty_text": rec["counterparty_text"] if is_txn else None,
        "datetime_local": dt_local if is_txn else None,
        "received_at_local": (dt + timedelta(seconds=rng.randint(0, 45))).strftime("%Y-%m-%dT%H:%M:%S"),
        "account_last4": acct4 if "{acct4}" in t["text"] else None,
        "card_last4": card4 if "{card4}" in t["text"] else None,
        "transaction_id": hexid if "{txid}" in t["text"] else None,
        "template_id": t["id"], "template_origin": t["origin"], "noise": noise, "source": "synthetic",
        "_base": rec["_base"],
    }


# --------------------------------------------------------------------------- #
# Dataset
# --------------------------------------------------------------------------- #
def choose_holdouts(templates, rng):
    groups = defaultdict(list)
    for t in templates:
        if not t["no_holdout"]:
            groups[(t["kind"], t["type"])].append(t["id"])
    held_t = set()
    for g, ids in groups.items():
        if len(ids) >= 3:
            held_t.update(rng.sample(ids, max(1, round(0.2 * len(ids)))))
    held_b = set()
    for cat, lst in NAMED.items():
        k = max(1, round(0.2 * len(lst)))
        held_b.update(f"named:{cat}:{en}" for en, _ in rng.sample(lst, k))
    held_b.update(f"proc:{n}" for n, _ in rng.sample(NAMES, round(0.2 * len(NAMES))))
    return held_t, held_b


def generate(seed, n_cat, n_neg):
    rng = random.Random(seed)
    templates = build_templates()
    by_cat, by_neg = defaultdict(list), defaultdict(list)
    for t in templates:
        if t["kind"] == "txn":
            for c in t["cats"]:
                by_cat[c].append(t)
        else:
            by_neg[t["type"]].append(t)

    rows, seen = [], set()

    def fill(pool, n, cat):
        made = tries = 0
        while made < n and tries < n * 8:
            tries += 1
            r = realize(rng.choice(pool), rng, cat=cat)
            if r["text"] in seen:
                continue
            seen.add(r["text"])
            rows.append(r)
            made += 1

    for c in ALL_CATEGORIES:
        fill(by_cat[c], n_cat, c)
    for typ, pool in by_neg.items():
        fill(pool, n_neg, None)

    held_t, held_b = choose_holdouts(templates, rng)
    rng.shuffle(rows)
    for i, r in enumerate(rows, 1):
        r["id"] = f"sms_{i:06d}"
        if r["template_id"] in held_t:
            r["split"] = "test_unseen_template"
        elif r["_base"] in held_b:
            r["split"] = "test_unseen_merchant"
        else:
            r["split"] = "train" if rng.random() < 0.9 else "validation"
        del r["_base"]
    return rows, templates, held_t, held_b


REAL = [
    {"id": "real_0001", "sender": "BDC",
     "text": "تم تنفيذ تحويل لحظي من حسابكم 5124 بمبلغ 200.00 جم في 11:44 يوم 11/6/26 رقم المعاملة b2df3ead "
             "للمزيد أتصل ب 16990",
     "amount": 200.0, "datetime_local": "2026-11-06T11:44:00", "received_at_local": "2026-11-06T11:44:00",
     "transaction_id": "b2df3ead"},
    {"id": "real_0002", "sender": "BDC",
     "text": "تم تنفيذ تحويل لحظي من حسابكم 5124 بمبلغ 226.00 جم في 15:41 يوم 11/12/26 رقم المعاملة 833c9197 "
             "للمزيد أتصل ب 16990",
     "amount": 226.0, "datetime_local": "2026-11-12T15:41:00", "received_at_local": "2026-11-12T15:41:00",
     "transaction_id": "833c9197"},
]


def real_records():
    out = []
    for r in REAL:
        out.append({**r, "text_norm": normalize(r["text"]), "language": "ar", "bank": "BANQUE_DU_CAIRE",
                    "sender_type": "bank", "is_transaction": True, "type": "transfer_out", "direction": "debit",
                    "category": "Transfer", "currency": "EGP", "merchant": None, "merchant_text": None,
                    "counterparty_text": None, "account_last4": "5124", "card_last4": None,
                    "template_id": "bdc_instant_transfer_out", "template_origin": "real", "noise": [],
                    "source": "real", "split": "real_test", "mentions_amount": True})
    return out


def write_json_array(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n]\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="./data")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-cat", type=int, default=600, help="rows per spending category")
    ap.add_argument("--n-neg", type=int, default=500, help="rows per non-transaction type")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    rows, templates, held_t, held_b = generate(a.seed, a.n_cat, a.n_neg)
    assert all(r["amount"] and r["category"] for r in rows if r["is_transaction"])
    assert not any(r["template_id"] in held_t and r["split"] in ("train", "validation") for r in rows)
    write_json_array(os.path.join(a.out, "sms_dataset.json"), rows)
    write_json_array(os.path.join(a.out, "real_sms_test.json"), real_records())

    stats = {
        "rows": len(rows),
        "by_split": Counter(r["split"] for r in rows),
        "is_transaction": Counter(r["is_transaction"] for r in rows),
        "by_category": Counter(r["category"] for r in rows if r["is_transaction"]),
        "by_non_txn_type": Counter(r["type"] for r in rows if not r["is_transaction"]),
        "by_language": Counter(r["language"] for r in rows),
        "by_template_origin": Counter(r["template_origin"] for r in rows),
        "n_templates": len(templates),
        "held_out_templates": sorted(held_t),
        "n_held_out_merchant_bases": len(held_b),
    }
    with open(os.path.join(a.out, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
