from datetime import datetime, timezone

from vera.conversations import ConversationBook

DIP = {"metric": "calls", "delta_pct": -0.5, "window": "7d", "vs_baseline": 12}
PLACEHOLDER = {"placeholder": True, "metric_or_topic": "x"}


def at(hour):
    return datetime(2026, 11, 6, hour, 0, tzinfo=timezone.utc)


def test_opening_a_conversation_records_the_first_message(add_trigger, brief_for):
    book = ConversationBook()
    brief = brief_for(add_trigger("t1", "perf_dip", "m_den", DIP))
    conversation = book.open("conv_1", brief, "Dr. Meera, hello", at(9))
    assert (conversation.merchant_id, conversation.kind, conversation.language) == ("m_den", "perf_dip", "hi-en")
    assert conversation.lead == brief.lead.text and conversation.status == "open"
    assert conversation.bot_bodies == ["Dr. Meera, hello"] and len(book) == 1
    assert book.get("conv_1") is conversation and book.get("nope") is None


def test_opening_twice_adds_nothing(add_trigger, brief_for):
    book = ConversationBook()
    brief = brief_for(add_trigger("t1", "perf_dip", "m_den", DIP))
    book.open("conv_1", brief, "first", at(9))
    book.open("conv_1", brief, "second", at(10))
    assert book.get("conv_1").bot_bodies == ["first"]


def test_replies_extend_a_thread_and_conversations_can_be_closed(add_trigger, brief_for):
    book = ConversationBook()
    brief = brief_for(add_trigger("t1", "perf_dip", "m_den", DIP))
    book.open("conv_1", brief, "hello", at(9))
    book.append("conv_1", "merchant", "yes please", at(10))
    book.append("conv_1", "vera", "done", at(11))
    assert [t.role for t in book.get("conv_1").turns] == ["vera", "merchant", "vera"]
    assert book.get("conv_1").bot_bodies == ["hello", "done"]
    assert book.append("missing", "merchant", "hi") is None
    book.close("conv_1", "merchant opted out")
    assert (book.get("conv_1").status, book.get("conv_1").closed_reason) == ("closed", "merchant opted out")


def test_what_a_person_was_already_sent_is_listed_oldest_first(add_trigger, brief_for):
    book = ConversationBook()
    dip = brief_for(add_trigger("t1", "perf_dip", "m_den", DIP))
    spike = brief_for(add_trigger("t2", "perf_spike", "m_den", PLACEHOLDER))
    customer = brief_for(add_trigger("t3", "appointment_tomorrow", "m_den", PLACEHOLDER, customer_id="c_priya"))
    book.open("conv_late", spike, "second message", at(12))
    book.open("conv_early", dip, "first message", at(9))
    book.open("conv_customer", customer, "to the customer", at(10))
    assert book.bodies_for(dip) == ["first message", "second message"]  # merchant-facing only
    assert book.bodies_for(customer) == ["to the customer"]
    assert len(book.for_merchant("m_den")) == 3
