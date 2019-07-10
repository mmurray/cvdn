<html>
<head>
<title>MP Dialog</title>

<!-- First include jquery js -->
<script src="//code.jquery.com/jquery-1.12.0.min.js"></script>
<script src="//code.jquery.com/jquery-migrate-1.2.1.min.js"></script>

<!-- Latest compiled and minified JavaScript -->
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>

<!-- Latest compiled and minified CSS -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">

<link rel="stylesheet" href="style.css">
</head>

<body>
<div id="container">

<?php
require_once('functions.php');

if (!isset($_POST['uid'])) {
  die("You must have found this page by accident.");
}
# Submitted survey.
else {

  $uid = $_POST['uid'];

  # Show exit instructions.
  $uid = $_POST['uid'];
  $mturk_code = $uid."_".substr(sha1("phm_salted_hash".$uid."thowpbr_main2"), 0, 13);
  ?>
  <div class="row">
    <div class="col-md-12">
      <p>
        Thank you for your participation!</p>
      <p>Copy the code below, return to Mechanical Turk, and enter it to receive payment:<br/>
        <b><?php echo $mturk_code; ?></b>
      </p>
    </div>
  </div>

<?php
  $pid = ($_POST['uid'] == $_POST['navigator'] ? $_POST['oracle'] : $_POST['navigator']);
  $data = array(
    "uid" => $_POST['uid'],
    "pid" => $pid,
    "oracle" => $_POST['oracle'],
    "navigator" => $_POST['navigator'],
    "rating" => $_POST['rating'],
    "problem" => $_POST['problem'],
    "free_form_feedback" => $_POST['free_form_feedback'],
  );
  write_file('feedback/' . $_POST['uid'] . '_' . $pid . '.json', json_encode($data) . "\n", 'Could not create file to save feedback.');
}
?>

</div>
</body>

</html>
