"""Sample app mutated by the codeflux demo."""


MAX_RETRIES = 3


def greet(name):
    return f"hello {name}"


def main():
    for i in range(MAX_RETRIES):
        print(greet("world"))


if __name__ == "__main__":
    main()
