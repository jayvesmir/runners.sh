"""
The Fun Bar Signature (or "fun bar" for short) is an EAN-8 barcode[^1] falling in the Restricted Circulation Numbers (aka private use) range. This is to make sure someone scanning a Fun Bar Signature with their phone won't turn up a package of frozen peas or whatever.

The choice of EAN-8 is because it's horizontal, it fits in the narrow height of the Fun Bar Signature, is decently short, and it has wide compatibility with phone scanners.

[1]: https://ref.gs1.org/standards/genspecs/, 1.4.5 for RCN range, 5.2.1 for the EAN-8 specification
"""

# A = NUMBER_SETS[digit]
# B = NUMBER_SETS[digit][::-1]
# C = NUMBER_SETS[digit] # but C has the dark bars first

NUMBER_SETS = [
	[3, 2, 1, 1],
	[2, 2, 2, 1],
	[2, 1, 2, 2],
	[1, 4, 1, 1],
	[1, 1, 3, 2],
	[1, 2, 3, 1],
	[1, 1, 1, 4],
	[1, 3, 1, 2],
	[1, 2, 1, 3],
	[3, 1, 1, 2],
]

assert all(len(widths) == 4 and sum(widths) == 7 for widths in NUMBER_SETS)

NORMAL_GUARD_BAR = [1, 1, 1]
CENTER_GUARD_BAR = [1, 1, 1, 1, 1]

type Barcode = int | str | list[int]


def barcode_to_digits(barcode: Barcode, num_digits=8) -> list[int]:
	if type(barcode) is int:
		barcode = str(barcode).zfill(num_digits)
	if type(barcode) is str:
		barcode = [*map(int, barcode)]

	assert type(barcode) is list  # for type checking
	assert len(barcode) in (7, 8), f"invalid barcode length: {len(barcode)}"
	assert barcode[0] in (2, 4), (
		f"invalid starting digit for {''.join(map(str, barcode))}, must start with 2 or 4 to be an RCN code (see comments of {__file__} for why)"
	)
	check_digit = check_digit_for(barcode)
	if len(barcode) == 7:
		barcode.append(check_digit)
	else:
		assert check_digit == barcode[7], (
			f"invalid check digit in {''.join(map(str, barcode))}, should be {check_digit}"
		)

	return barcode


def check_digit_for(digits: list[int]) -> int:
	return -sum(digit * (3, 1)[i % 2] for i, digit in enumerate(digits[:7])) % 10


def bar_widths_from_ean8(barcode: Barcode) -> list[int]:
	digits = barcode_to_digits(barcode)

	barcode = []
	barcode += NORMAL_GUARD_BAR
	for c in digits[:4]:
		barcode += NUMBER_SETS[c]
	barcode += CENTER_GUARD_BAR
	for c in digits[4:]:
		barcode += NUMBER_SETS[c]
	barcode += NORMAL_GUARD_BAR

	return barcode


_barcode_cache = None
_barcode_cache_path = None


def get_barcode_cache(output_path: str):
	global _barcode_cache, _barcode_cache_path

	# TODO: implement barcode cache as a file
	"""
	import os.path as path
	from solstice.log import warn

	if _barcode_cache is None:
		_barcode_cache_path = path.join(output_path, path.pardir, "barcode_cache.txt")
		try:
			with open(_barcode_cache_path, "r") as file:
				_barcode_cache = set(map(int, filter(len, file)))
		except (FileNotFoundError, ValueError) as e:
			_barcode_cache = set()

			if isinstance(e, ValueError):
				warn(
					f"Failed to parse barcode cache from {_barcode_cache_path}: {e.args[0]}. The barcode cache won't update until this is fixed (if nothing else, try removing the file)"
				)
				# set _barcode_cache_path to none to signal to flush_barcode_cache() that it shouldn't run
				_barcode_cache_path = None

		import atexit

		atexit.register(flush_barcode_cache)
	"""
	_barcode_cache = set()

	return _barcode_cache


def flush_barcode_cache():
	if _barcode_cache_path is None or _barcode_cache is None:
		return
	with open(_barcode_cache_path, "w") as file:
		file.writelines(f"{code:08}\n" for code in _barcode_cache)


def generate_rcn_barcode(dist_path) -> Barcode:
	"""
	Generates a random RCN (private use) barcode.
	"""
	import secrets  # because you can never be too sure

	for _ in range(1000):
		integer = secrets.randbits(128)

		# only 2 and 4 are valid RCN starting digits so just check a random bit to decide
		first_digit = (2, 4)[integer >> 127]

		barcode = f"{first_digit}{integer % 1000000:06}"
		barcode += str(check_digit_for([*map(int, barcode)]))
		if barcode not in get_barcode_cache(dist_path):
			return barcode

	raise RuntimeError(
		"Can't generate unique RCN code after 1000 tries. You're either the unluckiest person in the world or something is wrong with this function"
	)


SOLSTICE_PEPPER = b"\x97\xf2k\x82v\xbf8\xf7\x01\x123\x9a^\xfb&d"


def html_from_ean8(
	ean8,
	colors: list[str] = ["fg", "a1", "a2", "a3"],
	width_prefix: str = "w",
	element_name: str = "span",
	padding: int = 6,
):
	digits = barcode_to_digits(ean8)

	from random import Random

	rand = Random()
	rand.seed(bytes(digits))

	substrings = []

	is_gap = False

	def element(bar_widths, digit: int | None = None):
		nonlocal is_gap
		for i, bar_width in enumerate(bar_widths):
			children = []
			if i == 0 and digit is not None:
				children.append(f'<span class="digit {rand.choice(colors)}">{digit}</span>')
			substrings.append(
				f'<{element_name} class="segment {width_prefix}{bar_width} {rand.choice(colors)} {"gap" if is_gap else "fill"}">{"".join(children)}</{element_name}>'
			)
			is_gap = not is_gap

	# TODO: light mode barcodes
	if padding > 0:
		element((padding,))
	substrings.append('<span class="main-barcode">')
	element(NORMAL_GUARD_BAR)
	for c in digits[:4]:
		element(NUMBER_SETS[c], c)
	element(CENTER_GUARD_BAR)
	for c in digits[4:]:
		element(NUMBER_SETS[c], c)
	element(NORMAL_GUARD_BAR)
	substrings.append("</span>")
	if padding > 0:
		element((padding,))

	return "".join(substrings)
	# return ""
