from ivm.lexer import (
    Lexer,
    global_,
    open_brace,
    close_brace,
    open_paren,
    close_paren,
    ident_,
    n32,
    at,
    question,
)


def test_tokenize():
    assert (
        list(
            t
            for t, _ in Lexer(
                """
::std::numeric { /* /* hellow */ a */ fn(dup43(n0 @n32_ne(0 ?(a b c))) n1) }
""".splitlines()
            ).tokenize()
        )
        == [
            global_,
            open_brace,
            ident_,
            open_paren,
            ident_,
            open_paren,
            ident_,
            at,
            ident_,
            open_paren,
            n32,
            question,
            open_paren,
            ident_,
            ident_,
            ident_,
            close_paren,
            close_paren,
            close_paren,
            ident_,
            close_paren,
            close_brace,
        ]
    )
