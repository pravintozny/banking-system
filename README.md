# banking-system

## Customer management

`customer_management` provides a `Customer` model and an in-memory `CustomerService`
with `create`, `get`, `update`, `delete` and `list(search=...)`. Names are required,
email and phone are validated, and email is unique (case-insensitive).

```python
from customer_management import CustomerService
svc = CustomerService()
c = svc.create("Ada", "Lovelace", "ada@example.com")
```

Run tests: `python -m unittest discover -s tests -t .`
