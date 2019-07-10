<?php
require_once('functions.php');

$fn = urldecode($_GET['fn']);
$opt = $_GET['opt'];
clearstatcache();

# Validate filename.
$parts = explode('/', $fn);
if (strcmp($parts[0], "client") != 0) {
	die("0");  // invalid path
}
$parts = explode('.', $fn);
if (strcmp($parts[count($parts)-1], "json") != 0) {
	die("0");  // invalid extension
}

# Exists option.
if (strcmp($opt, "exists") == 0) {
	if (is_file($fn)) {
		echo "1";
	} else {
		echo "0";
	}
}

# Read option.
elseif (strcmp($opt, "read") == 0) {
	$d = read_file($fn);
	if ($d) {
		echo $d;
	} else {
		echo "0";
	}
}

# Write option.
elseif (strcmp($opt, 'write') == 0) {
	$m = urldecode($_GET['m']);
	write_file($fn, $m, "0");  # if this fails, page dies with '0'
	echo "1";
}

# Delete option.
elseif (strcmp($opt, 'del') == 0) {
	delete_file($fn, "0");  # if this failed, page dies with '0'
	echo "1";
}

# Unrecognized option.
else {
	echo "0";
}

?>
