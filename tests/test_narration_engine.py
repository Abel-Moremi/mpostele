from app.media.narration_engine import split_into_segments


def test_splits_on_sentence_boundaries():
    text = (
        "Stop wrestling with setup scripts. "
        "Our CLI gets your containers running in one command, every time, on every machine. "
        "No more onboarding docs that go stale."
    )
    segments = split_into_segments(text)
    assert segments == [
        "Stop wrestling with setup scripts.",
        "Our CLI gets your containers running in one command, every time, on every machine.",
        "No more onboarding docs that go stale.",
    ]


def test_merges_short_leading_piece_forward():
    text = "Hi. This is a longer sentence that continues on for quite a while. Bye."
    segments = split_into_segments(text)
    # "Hi." and the trailing "Bye." are both under the char threshold and
    # have no other short neighbor to combine with beyond the long middle
    # sentence, so everything folds into one segment.
    assert segments == [text]


def test_merges_several_short_pieces_until_threshold_cleared():
    text = "Wow. Ok. Great. This is fine now for real this time honestly."
    segments = split_into_segments(text)
    assert segments == [text]


def test_single_short_sentence_is_its_own_segment():
    text = "Just one short sentence."
    assert split_into_segments(text) == [text]


def test_whole_text_short_with_only_periods():
    text = "A. B. C."
    assert split_into_segments(text) == [text]


def test_empty_text_returns_single_empty_segment():
    assert split_into_segments("") == [""]


def test_long_sentences_each_stay_their_own_segment():
    a = "This first sentence is easily long enough to clear the merge threshold on its own."
    b = "So is this second one, comfortably past twenty five characters in length."
    segments = split_into_segments(f"{a} {b}")
    assert segments == [a, b]
