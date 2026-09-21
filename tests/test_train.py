"""
train.py testleri -- permutation importance siralamasi.

feature_importance.csv repoda duruyor ve CPP listesi ondan okunuyor. Siralama
kararsiz olursa ayni kod ayni veriyle farkli bir top-8 yazar: rapor "degismis"
gorunur ama hicbir sey degismemistir. 17 Eylul'de olculen durum buydu --
n_jobs=-1 paralel toplamasi degerlerin son bitlerini oynatiyor ve onemi tam
0 olan uc degisken 8. sira icin berabere kaliyordu.
"""
import train


def _row(feature, imp, std=0.0):
    return dict(output="Stage1.M13", feature=feature, imp=imp, std=std)


def test_rank_orders_by_importance_descending():
    rows = [_row("a", 0.1), _row("b", 0.5), _row("c", 0.3)]

    assert [r["feature"] for r in train.rank_importances(rows, top=3)] == ["b", "c", "a"]


def test_rank_breaks_ties_by_name_not_input_order():
    tied = [_row("Machine5.Temperature3", 0.0), _row("Machine1.MotorRPM", 0.0),
            _row("Machine3.Zone1Temperature", 0.0)]

    for rows in (tied, tied[::-1], tied[1:] + tied[:1]):
        top = train.rank_importances([_row("x", 0.2)] + rows, top=2)
        assert [r["feature"] for r in top] == ["x", "Machine1.MotorRPM"]


def test_rank_is_stable_under_last_bit_noise():
    # Ayni hesabin iki calismasi: fark yalnizca ~1e-16 (paralel toplama sirasi)
    run1 = [_row("p", train.round5(0.0006773807120371344)),
            _row("q", train.round5(0.0006773807120376673))]
    run2 = [_row("p", train.round5(0.0006773807120376673)),
            _row("q", train.round5(0.0006773807120371344))]

    assert train.rank_importances(run1, 2) == train.rank_importances(run2, 2)


def test_rank_top_truncates():
    rows = [_row(str(i), i / 10) for i in range(10)]

    assert len(train.rank_importances(rows, top=8)) == 8
    assert len(train.rank_importances(rows[:3], top=8)) == 3


def test_round5_turns_negative_zero_into_zero():
    assert str(train.round5(-0.0)) == "0.0"
    assert str(train.round5(-1e-12)) == "0.0"
    assert train.round5(0.123456789) == 0.12346


def test_short_name():
    assert train.short_name("Machine1.MotorRPM.C.Actual") == "Machine1.MotorRPM"
    assert (train.short_name("FirstStage.CombinerOperation.Temperature3.C.Actual")
            == "Combiner.Temperature3")
