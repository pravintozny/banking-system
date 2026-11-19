import unittest

from customer_management import (
    CustomerService,
    CustomerNotFoundError,
    DuplicateEmailError,
    ValidationError,
)


class CustomerServiceTests(unittest.TestCase):
    def setUp(self):
        self.svc = CustomerService()
        self.c = self.svc.create("Ada", "Lovelace", "Ada@Example.com", "+44 1234567", "London")

    def test_create_normalizes_and_assigns_id(self):
        self.assertEqual(self.c.id, 1)
        self.assertEqual(self.c.email, "ada@example.com")
        self.assertEqual(self.svc.create("A", "B", "a@b.co").id, 2)

    def test_create_validation(self):
        with self.assertRaises(ValidationError):
            self.svc.create("", "X", "x@y.com")
        with self.assertRaises(ValidationError):
            self.svc.create("X", "Y", "not-an-email")
        with self.assertRaises(ValidationError):
            self.svc.create("X", "Y", "x@y.com", phone="abc")

    def test_unique_email_case_insensitive(self):
        with self.assertRaises(DuplicateEmailError):
            self.svc.create("B", "C", "ADA@example.com")

    def test_get_and_not_found(self):
        self.assertIs(self.svc.get(1), self.c)
        with self.assertRaises(CustomerNotFoundError):
            self.svc.get(99)

    def test_update(self):
        u = self.svc.update(1, last_name="King", email="new@example.com")
        self.assertEqual((u.last_name, u.email, u.first_name), ("King", "new@example.com", "Ada"))
        self.assertEqual(self.svc.get(1).email, "new@example.com")
        # old email is freed
        self.svc.create("Z", "Z", "ada@example.com")

    def test_update_own_email_ok_and_conflict(self):
        self.svc.update(1, email="ADA@example.com")
        other = self.svc.create("B", "C", "b@c.com")
        with self.assertRaises(DuplicateEmailError):
            self.svc.update(other.id, email="ada@example.com")
        self.assertEqual(self.svc.get(other.id).email, "b@c.com")

    def test_update_invalid(self):
        with self.assertRaises(ValidationError):
            self.svc.update(1, id=5)
        with self.assertRaises(ValidationError):
            self.svc.update(1, email="bad")
        with self.assertRaises(CustomerNotFoundError):
            self.svc.update(42, phone="")

    def test_delete_frees_email(self):
        self.svc.delete(1)
        with self.assertRaises(CustomerNotFoundError):
            self.svc.get(1)
        self.assertEqual(self.svc.create("N", "M", "ada@example.com").id, 2)
        with self.assertRaises(CustomerNotFoundError):
            self.svc.delete(1)

    def test_list_and_search(self):
        self.svc.create("Bob", "Stone", "bob@x.com")
        self.assertEqual([c.id for c in self.svc.list()], [1, 2])
        self.assertEqual([c.id for c in self.svc.list(search="stone")], [2])
        self.assertEqual(self.svc.list(search="nomatch"), [])


if __name__ == "__main__":
    unittest.main()
