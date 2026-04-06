from tests.conftest import run_program


def test_hihi(host):
    output = run_program(host, "hihi.iv")
    assert output == "hi\nhi\n"


def test_fizzbuzz(host):
    output = run_program(host, "fizzbuzz.iv")
    expected_lines = []
    for n in range(1, 21):
        if n % 15 == 0:
            expected_lines.append("FizzBuzz")
        elif n % 3 == 0:
            expected_lines.append("Fizz")
        elif n % 5 == 0:
            expected_lines.append("Buzz")
        else:
            expected_lines.append(str(n))
    expected = "\n".join(expected_lines) + "\n"
    assert output == expected


def test_cat(host):
    output = run_program(host, "cat.iv", stdin_data="hello")
    assert output == "hello"
