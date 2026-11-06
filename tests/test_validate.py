"""The validator is the last gate before a message leaves the bot, so each rule gets its own test."""
from dataclasses import replace

import pytest

from vera.validate import _licensed, check, numbers_of

SLOTS = [
    {"iso": "2026-11-05T18:00:00+05:30", "label": "Wed 5 Nov, 6pm"},
    {"iso": "2026-11-06T17:00:00+05:30", "label": "Thu 6 Nov, 5pm"},
]
DIP = {"metric": "calls", "delta_pct": -0.5, "window": "7d", "vs_baseline": 12}
RECALL = {"service_due": "6_month_cleaning", "last_service_date": "2026-05-12", "due_date": "2026-11-12", "available_slots": SLOTS}
PLACEHOLDER = {"placeholder": True, "metric_or_topic": "x"}

# One message that is fine for each of the three briefs below.
EN_DIP = ("Dr. Sameer, your calls are down 50% over the last 7 days, against a baseline of 12. "
          "Want me to look into what changed and send you a short fix list? Reply YES.")
HINGLISH_DIP = ("Dr. Meera, aapke calls pichhle 7 days mein 50% neeche hain, baseline 12 tha. "
                "Kya main dekh loon ki kya badla aur ek chhoti fix list bhej doon? YES bhej dijiye.")
RECALL_BODY = ("Hi Priya, Dr. Meera's Dental Clinic here. Your 6-month cleaning is due 12 Nov; last done 12 May. "
               "Dental Cleaning @ ₹299 is on. Reply 1 for Wed 5 Nov, 6pm; 2 for Thu 6 Nov, 5pm; ya koi aur time bata dijiye.")


@pytest.fixture
def sam(add_trigger, brief_for):
    """An English-speaking merchant with no earlier conversation."""
    return brief_for(add_trigger("t_sam", "perf_dip", "m_sam", DIP, urgency=4))


@pytest.fixture
def meera(add_trigger, brief_for):
    """A Hinglish-speaking merchant who has talked to Vera before."""
    return brief_for(add_trigger("t_meera", "perf_dip", "m_den", DIP, urgency=4))


@pytest.fixture
def priya(add_trigger, brief_for):
    """A Hinglish-speaking customer being offered two slots."""
    return brief_for(add_trigger("t_priya", "recall_due", "m_den", RECALL, customer_id="c_priya", urgency=3))


def codes(body, brief, seen=()):
    return [p.code for p in check(body, brief, seen)]


def test_grounded_messages_pass(sam, meera, priya):
    assert check(EN_DIP, sam) == []
    assert check(HINGLISH_DIP, meera) == []
    assert check(RECALL_BODY, priya) == []


# --------------------------------------------------------------------------- numbers

def test_numbers_are_read_the_way_people_write_them():
    assert numbers_of("₹1,499/month, 3.0% and Studio11 on 12 Nov, batch AT2024-1102, vitamin B12") == ["1499", "3", "12", "1102"]


def test_a_number_that_is_not_in_the_facts_is_flagged(sam):
    problems = check(EN_DIP.replace("50%", "70%"), sam)
    assert [p.code for p in problems] == ["number"]
    assert "70" in problems[0].detail


def test_small_effort_estimates_are_not_claims_about_the_business(sam):
    assert check(EN_DIP.replace("Want me", "It is a 5-min job. Want me"), sam) == []
    assert codes(EN_DIP.replace("Want me", "It is a 45-min job. Want me"), sam) == ["number"]


def test_day_counts_license_the_same_span_in_weeks_and_months():
    assert {"90", "13", "3"} <= _licensed(["plan expired 90 days ago"])
    assert "13" not in _licensed(["plan expired 91 months ago"])


# --------------------------------------------------------------------------- patterns

@pytest.mark.parametrize("insert", [
    "Details at www.example.com.", "Visit https://x.in/offer.", "Mail help@shop.com.", "Call 98765 43210.", "Call 9876543210.",
])
def test_links_emails_and_phone_numbers_are_flagged(sam, insert):
    assert "url" in codes(EN_DIP.replace("Want me", f"{insert} Want me"), sam)


def test_forbidden_wording_is_flagged(sam):
    assert "taboo" in codes(EN_DIP.replace("Want me", "Results are guaranteed. Want me"), sam)
    strict = replace(sam, category={**sam.category, "voice": {"vocab_taboo": ["cure (without disclosure)"]}})
    assert "taboo" in codes(EN_DIP.replace("Want me", "A cure for slow weeks. Want me"), strict)
    assert "taboo" not in codes(EN_DIP, strict)


@pytest.mark.parametrize("word", ["trigger", "{name}", "[Merchant]", "m_den_1", "null", "CTA", "json"])
def test_internal_wording_is_flagged(sam, word):
    assert "jargon" in codes(EN_DIP.replace("Want me", f"Note: {word}. Want me"), sam)


def test_repeating_an_earlier_message_is_flagged(sam):
    assert "repeat" in codes(EN_DIP, sam, seen=[EN_DIP])
    nearly = EN_DIP.replace("look into what changed", "check what changed")
    assert "repeat" in codes(nearly, sam, seen=[EN_DIP])
    assert "repeat" in codes(EN_DIP, replace(sam, prior_bodies=(EN_DIP,)))
    assert "repeat" not in codes(EN_DIP, sam, seen=["Hello there, a completely different message about something else."])


# --------------------------------------------------------------------------- who it is for

def test_the_recipient_must_be_addressed_by_name(sam, priya):
    assert "no_name" in codes(EN_DIP.replace("Dr. Sameer, ", ""), sam)
    assert "business" in codes(RECALL_BODY.replace("Dr. Meera's Dental Clinic", "Our clinic"), priya)
    assert "vera" in codes(RECALL_BODY.replace("here.", "here, Vera's partner."), priya)


def test_a_message_about_a_child_names_the_child(add_trigger, brief_for):
    brief = brief_for(add_trigger("t", "recall_due", "m_den", PLACEHOLDER, customer_id="c_kid"))
    body = "Hi Sneha, Dr. Meera's Dental Clinic here. It is time for the next regular visit. Shall we book a slot? Reply YES."
    assert "no_name" in codes(body, brief)
    assert "no_name" not in codes(body.replace("the next", "Aanya's next"), brief)


def test_vera_does_not_introduce_herself_again(meera):
    assert "reintro" in codes(HINGLISH_DIP.replace("Dr. Meera,", "Dr. Meera, main Vera hoon."), meera)
    assert "reintro" not in codes(HINGLISH_DIP, meera)


# --------------------------------------------------------------------------- the ask

def test_there_must_be_exactly_one_ask_and_it_comes_last(sam):
    assert "ask" in codes("Dr. Sameer, your calls are down 50% over the last 7 days, against a baseline of 12.", sam)
    assert "ask" in codes(EN_DIP.replace("Want me", "Why is that? Want me"), sam)
    assert "ask" in codes(EN_DIP + " Thanks " + "x" * 200, sam)


def test_slot_and_confirm_requirements(priya, add_trigger, brief_for):
    wrong_slots = RECALL_BODY.replace("Wed 5 Nov, 6pm", "Wednesday evening").replace("Thu 6 Nov, 5pm", "Thursday")
    assert "slots" in codes(wrong_slots, priya)

    appointment = brief_for(add_trigger("t2", "appointment_tomorrow", "m_den", PLACEHOLDER, customer_id="c_priya"))
    good = "Hi Priya, Dr. Meera's Dental Clinic here. Aapki appointment kal hai. Reply CONFIRM ya koi aur time bata dijiye."
    assert check(good, appointment) == []
    assert "ask" in codes("Hi Priya, Dr. Meera's Dental Clinic here. Aapki appointment kal hai. Kya aap aa sakte hain?", appointment)


# --------------------------------------------------------------------------- language and length

def test_language_follows_the_recipients_preference(sam, meera):
    assert "language" in codes(HINGLISH_DIP.replace("Dr. Meera", "Dr. Sameer"), sam)   # Hinglish to an English reader
    assert "language" in codes(EN_DIP.replace("Dr. Sameer", "Dr. Meera"), meera)       # plain English to a Hinglish reader
    devanagari = "Dr. Meera, आपके calls 7 days में 50% कम हैं। क्या मैं मदद करूँ? YES भेजिए।"
    assert "language" not in codes(devanagari, meera)


def test_length_limits(sam):
    assert codes("Hi", sam) == ["too_short"]
    assert "too_long" in codes(EN_DIP + " " + "word " * 200, sam)
