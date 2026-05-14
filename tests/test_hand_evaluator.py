from game import Card, HandEvaluator


def cards(text: str):
    return [Card.from_code(code) for code in text.split()]


def test_high_card():
    result = HandEvaluator.evaluate(cards("Ah Kd 8c 5s 2h"))
    assert result.rank == 0
    assert result.values == (14, 13, 8, 5, 2)


def test_one_pair():
    result = HandEvaluator.evaluate(cards("Ah Ad 8c 5s 2h"))
    assert result.rank == 1
    assert result.values == (14, 8, 5, 2)


def test_two_pair():
    result = HandEvaluator.evaluate(cards("Ah Ad 8c 8s 2h"))
    assert result.rank == 2
    assert result.values == (14, 8, 2)


def test_three_of_a_kind():
    result = HandEvaluator.evaluate(cards("Ah Ad Ac 8s 2h"))
    assert result.rank == 3
    assert result.values == (14, 8, 2)


def test_straight():
    result = HandEvaluator.evaluate(cards("9h 8d 7c 6s 5h"))
    assert result.rank == 4
    assert result.values == (9,)


def test_low_ace_straight():
    result = HandEvaluator.evaluate(cards("Ah 2d 3c 4s 5h"))
    assert result.rank == 4
    assert result.values == (5,)


def test_flush():
    result = HandEvaluator.evaluate(cards("Ah Kh 8h 5h 2h"))
    assert result.rank == 5


def test_full_house():
    result = HandEvaluator.evaluate(cards("Ah Ad Ac 8s 8h"))
    assert result.rank == 6
    assert result.values == (14, 8)


def test_four_of_a_kind():
    result = HandEvaluator.evaluate(cards("Ah Ad Ac As 8h"))
    assert result.rank == 7
    assert result.values == (14, 8)


def test_straight_flush():
    result = HandEvaluator.evaluate(cards("Ah Kh Qh Jh Th"))
    assert result.rank == 8
    assert result.values == (14,)


def test_best_five_from_seven_cards():
    result = HandEvaluator.evaluate(cards("Ah Kh Qh Jh Th 2c 3d"))
    assert result.rank == 8


def test_compare_hands():
    assert HandEvaluator.compare(cards("Ah Ad 8c 5s 2h"), cards("Kh Kd Qc Js 9h")) == 1
    assert HandEvaluator.compare(cards("Ah Kd 8c 5s 2h"), cards("Ac Ks 8d 5c 2s")) == 0
