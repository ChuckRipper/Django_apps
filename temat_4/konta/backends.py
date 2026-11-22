"""Backend logowania: zablokowane konto nie zaloguje się, a otwarta sesja wygasa."""

from django.contrib.auth.backends import ModelBackend


class TylkoNiezablokowaniBackend(ModelBackend):
    def user_can_authenticate(self, user) -> bool:
        # Wywoływane przy logowaniu ORAZ przy każdym żądaniu (get_user) –
        # nałożenie blokady wylogowuje użytkownika przy następnym kliknięciu.
        return super().user_can_authenticate(user) and not getattr(user, "jest_zablokowany", False)
