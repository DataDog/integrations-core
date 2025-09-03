from unittest.mock import MagicMock

m = MagicMock()
m.side_effect = [print("Hi")]

m()
m()
