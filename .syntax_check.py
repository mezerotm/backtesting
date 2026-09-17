import ast, sys
files = ['server/api/auth.py', 'server/api/orders.py', 'server/api/dividends.py']
for f in files:
    try:
        with open(f) as fh:
            ast.parse(fh.read())
        print(f"{f}: OK")
    except SyntaxError as e:
        print(f"{f}: SYNTAX ERROR — {e}")
        sys.exit(1)
print("All files OK")
