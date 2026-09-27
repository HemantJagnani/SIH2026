import re
from bs4 import BeautifulSoup
from pathlib import Path

html_p = Path("runtime/evidence/2026-09-26/source=easemytrip/run=a2f475ae-4704-4d29-993f-c99cfb2a5826/page.html")
soup = BeautifulSoup(html_p.read_text(encoding="utf-8", errors="ignore"), "html.parser")
cards = soup.select(".nw_listing_bx")
print(f"Total cards: {len(cards)}")

def parse_option_details(box_text):
    cabin_kg = None
    checkin_kg = None
    cancel_fee = None
    change_fee = None
    refund_status = None

    # Cabin baggage: e.g. "7 Kgs Cabin Baggage" or "7 Kgs Cabin"
    m_cabin = re.search(r'(\d+)\s*Kgs?\s*Cabin', box_text, re.IGNORECASE)
    if m_cabin:
        cabin_kg = float(m_cabin.group(1))

    # Check-in baggage: e.g. "15 Kgs Check-in Baggage" or "15 Kgs Check-in"
    m_checkin = re.search(r'(\d+)\s*Kgs?\s*Check-in', box_text, re.IGNORECASE)
    if m_checkin:
        checkin_kg = float(m_checkin.group(1))

    # Cancellation fee: e.g. "Cancellation fee starts at ₹ 4,299" or "₹ 4,299 Onwards"
    m_cancel = re.search(r'Cancellation\s*fee\s*starts\s*at\s*[₹Rs\.]*\s*([\d,]+)', box_text, re.IGNORECASE)
    if m_cancel:
        cancel_fee = float(m_cancel.group(1).replace(",", ""))
        refund_status = "CONDITIONAL"
    elif "Non-Refundable" in box_text or "Non Refundable" in box_text:
        refund_status = "NON_REFUNDABLE"
    elif "Refundable" in box_text:
        refund_status = "REFUNDABLE"

    # Change fee: e.g. "Date Change fee starts at ₹ 3,499" or "₹ 0"
    m_change = re.search(r'Date\s*Change\s*fee\s*starts\s*at\s*[₹Rs\.]*\s*([\d,]+)', box_text, re.IGNORECASE)
    if m_change:
        change_fee = float(m_change.group(1).replace(",", ""))

    return {
        "cabin_baggage_kg": cabin_kg,
        "checkin_baggage_kg": checkin_kg,
        "cancellation_fee": cancel_fee,
        "change_fee": change_fee,
        "refund_status": refund_status,
    }

# Test across all cards and options
all_extracted = []
for i, card in enumerate(cards):
    option_boxes = card.select("._mfarebx, label:has(.fareheader), div:has(> .fareheader)")
    for b in option_boxes:
        hdr = b.select_one(".fareheader")
        prc = b.select_one(".fareprice")
        if hdr and prc:
            txt = " ".join(b.stripped_strings)
            details = parse_option_details(txt)
            all_extracted.append((hdr.get_text(strip=True), details))

print(f"Total options extracted with details: {len(all_extracted)}")
print("\nSample 5 extracted details:")
for fam, det in all_extracted[:5]:
    print(f"  Fare family: {fam} -> {det}")

from collections import Counter
print("\nBaggage check-in distribution:", Counter(d["checkin_baggage_kg"] for _, d in all_extracted))
print("Baggage cabin distribution:", Counter(d["cabin_baggage_kg"] for _, d in all_extracted))
print("Refund status distribution:", Counter(d["refund_status"] for _, d in all_extracted))
print("Cancellation fee min/max:", min(d["cancellation_fee"] for _, d in all_extracted if d["cancellation_fee"]), max(d["cancellation_fee"] for _, d in all_extracted if d["cancellation_fee"]))
