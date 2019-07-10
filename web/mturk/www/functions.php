<?php

// Read a file.
// fn - the filename
// returns a string of file contents or false
function read_file($fn) {
	$cmd = "cat " . $fn;
	$d = shell_exec($cmd);
	if (!$d || strcmp("cat:", substr($d, 0, 4)) == 0) {
		return false;
	} else {
		return $d;
	}
}

// Write to file.
// fn - the filename
// data - the data to put in the file
// err_msg - the error message to display if getting the file handle fails
function write_file($fn, $data, $err_msg) {
	$f = fopen($fn, 'w') or die($err_msg);
	fwrite($f, $data);
	fclose($f);
}

function append_file($fn, $data, $err_msg) {
	$f = fopen($fn, 'a') or die($err_msg);
	fwrite($f, $data);
	fclose($f);
}

// Unlink the given file.
// fn - said filename
// err_msg = the error message to display if unlinking the filename fails
function delete_file($fn, $err_msg) {
	unlink($fn) or die($err_msg);
}

?>