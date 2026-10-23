# Development evidence

E1's custom double-SEQ gate was reached after the stock gesture had already
changed page; owner could not test the feature. E3 removes that gesture and
uses the traced native view arrow switch instead.

Initial E3 controller fixtures failed because their model-type stub returned
track type 14 only for one pointer address, not for another pointer containing
the same owner handle; native code correctly refused invalid capture. A separate
fixture assumed every text override was non-null, although native clearing
accepts NULL. The first dynamic bank clear also exceeded the old fixture's
100k-instruction ceiling. Corrected those services and raised only the test
budget, then added an actual native widget-clear test. Final 11 E3 controller
checks and all other release checks pass. No failed image was delivered.

The inherited K16 header-location assertion was changed only in the E3 runner
from table offset 8 to 12, reflecting requested relocation to encoders 7/8.
Original K16 source/tests remain unchanged. Final isolated source checks and
independent rebuild verify the delivered image/source pairing.
