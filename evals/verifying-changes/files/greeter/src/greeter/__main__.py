import sys

from greeter import greet

print(greet(" ".join(sys.argv[1:]) or "world"))
