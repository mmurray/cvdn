<html>
<head>
<title>Room to Room Dialog</title>

<!-- First include jquery js -->
<script src="//code.jquery.com/jquery-1.12.0.min.js"></script>
<script src="//code.jquery.com/jquery-migrate-1.2.1.min.js"></script>

<!-- Latest compiled and minified JavaScript -->
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>

<!-- Latest compiled and minified CSS -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">

<link rel="stylesheet" href="style.css">

<link id="favicon" rel="shortcut icon" href="/favicon.ico">


<script>
    function setup_page(){
        // Check that Chrome is the browser and allow the HIT to load if it is.
        var is_chrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
        var is_firefox = /Firefox/.test(navigator.userAgent);
        if(!(is_chrome || is_firefox)) {
            $('#body_container').html("<div class=\"center\" style=\"font-size:130%;padding-top:100px\">This HIT requires <b><a href=\"https://www.google.com/chrome/\" target=\"_blank\">Google Chrome</a></b> or <b><a href=\"https://www.mozilla.org/en-US/firefox/new/\" target=\"_blank\">Firefox</a></b>.<br/>Please return the HIT and accept it using a compatible browser.</div>");
        }
    }
</script>

<script type="text/javascript">

var unloadListener = function(){ return "Please do not reload or close this tab! Doing so will abandon this game and strand your partner, and you will not be able to complete the HIT." };

// Whether to show debug messages.
var debug = true;

// Global vars for the script
var iv;  // the interval function that polls for Server response
var num_polls_since_last_message = 0;  // the number of times we've polled and gotten no response
// urls the agent uses to communicate with this user
var server_comm_url;
var client_comm_url;

var scan;  // the house index.
var target_obj;  // the target object.
var inst;  // instructions based on target object.
var start_pano;  // the starting panorama.
var end_panos;  // the target, ending panorama.
var curr_location_img_id;  // the current pano the navigator is at.
var feedback_metadata; // metadata required for submitting feedback

// Functions related to server-side processing.

// Get the contents of the given url, then delete the underlying file.
// url - url to get from and then delete
// returns - the contents of the url page
function get_and_delete_file(url) {
  var read_url = "manage_files.php?opt=read&fn=" + encodeURIComponent(url) + "&v=" + Math.floor(Math.random() * 999999999).toString();
  var contents = http_get(read_url);
  if (contents == "0") {  // file not written
    return false;
  } else {

    // delete the read file
    var del_url = "manage_files.php?opt=del&fn=" + encodeURIComponent(url);
    success = http_get(del_url);
    if (success == "0") {
      show_error("Failed to delete file '" + url + "' using url '" + del_url + "'.");
    }

    return contents;
  }
}

// Get the contents of the given url.
// url - said url
// Implementation from: https://stackoverflow.com/questions/247483/http-get-request-in-javascript
function http_get(url)
{
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.open("GET", url, false); // false for synchronous request
    xmlHttp.send(null);
    return xmlHttp.responseText;
}

// Check whether the given url returns a 404.
// url - the url to check
// returns bool
function url_exists(url) {
  var check_url = "manage_files.php?opt=exists&fn=" + encodeURIComponent(url);
  var exists = http_get(check_url);
  if (exists == "1") {
    return true;
  } else {
    return false;
  }
}

// Functions related to client-side processing.

// ----------
// Setters.

function set_house(v) {
  add_debug("set_house called with '" + v + "'");
  scan = v;
}

function set_target_obj(v) {
  add_debug("set_target_obj called with '" + v + "'");
  target_obj = v;
  inst = "Hint: The goal room contains a " + target_obj + ".";
}

function set_start_pano(v) {
  add_debug("set_start_pano called with '" + v + "'");
  start_pano = v;
  curr_location_img_id = v;
}

function set_end_panos(v) {
  add_debug("set_end_panos called with '" + v + "'");
  end_panos = v.split(",");
}

// ----------
// Chat interface.

function show_chat() {
  add_debug("show_chat called");
  $('#dialog_div').show();
}

function fmt_time_secs(s){return(s-(s%=60))/60+(9<s?':':':0')+Math.floor(s)}

// Enable the user text input.
function enable_chat(timeout_at) {
  add_debug("enable_chat called");
  $('#user_input').prop("disabled", false);
  $('#user_input').focus();
  $('#user_say').prop("disabled", false);
  $('#user_input_message').hide();


  if (timeout_at) {
      window.timeout_at = timeout_at;
      var time_left = timeout_at - Math.floor(Date.now() / 1000);
      $('#time_left_label').html("You have");
      $('#time_left_value').html(fmt_time_secs(time_left));
      $('#time_left').show();
  }
}

// Disable user text input.
function disable_chat(timeout_at) {
  add_debug("disable_chat called");
  $('#user_input').prop("disabled", true);
  $('#user_say').prop("disabled", true);
  $('#user_input_message').show();

  if (timeout_at) {
      window.timeout_at = timeout_at;
      var time_left = timeout_at - Math.floor(Date.now() / 1000);
      $('#time_left_value').html(fmt_time_secs(time_left));
      $('#time_left_label').html("Your partner has");
      $('#time_left').show();
  }
}

var blinkTimeout = null;
var animInterval = null;
var timerInterval = setInterval(function() {
    if (!window.timeout_at) return;
    var time_left = window.timeout_at - Math.floor(Date.now() / 1000);
    if (time_left < 0) time_left = 0;
    $('#time_left_value').html(fmt_time_secs(time_left));
}, 1000);

// Add a chat to either the user or partner dialog row and open the next row for typing.
function add_chat(message, speaker) {
  add_debug("add_chat called with " + speaker + " and " + message);
  var table = $('#dialog_table');
  var row_type = (speaker == "self" ? "chat_you_row" : "chat_partner_row");
  var markup = "<tr class=\"" + row_type + "\"><td>" + message + "</td></tr>";
  $("#dialog_table tbody").append(markup);
  if (speaker !== "self") {
    window.playSound(440.0, 'sine');
    clearTimeout(blinkTimeout);
    clearInterval(animInterval);
    blinkTimeout = setTimeout(function() {
        clearInterval(animInterval);
        $('#favicon').attr('href', '/favicon.ico');
    }, 20000);
    animInterval = setInterval(function() {
        if ($('#favicon').attr('href') == '/favicon-alert.ico') {
            $('#favicon').attr('href', '/favicon.ico');
        } else {
            $('#favicon').attr('href', '/favicon-alert.ico');
        }
    }, 500);
  }
}

function send_user_chat() {
  add_debug("send_user_chat called");
  var m = $('#user_input').val().trim().replace(/"/g, "'");  // read the value and strip it, replace double w single quotes
  if (m.length == 0) {
    return
  }
  $('#user_input').val('');  // clear user text
  var data = {type:"update", action:"chat", message:m};
  var url = "manage_files.php?opt=write&fn=" + client_comm_url + "&m=" + encodeURIComponent(JSON.stringify(data));
  var success = http_get(url);
  if (success == "0") {
    show_error("Failed to write file '" + client_comm_url + "' with message contents '" + m + "'.<br>Attempt made with url '" + url + "'.");
  }
  display_aux_message('');
  disable_chat();
}

function send_user_stop() {
  add_debug("send_user_stop called");
  var data = {type:"update", action:"guess_stop", value:curr_location_img_id};
  var url = "manage_files.php?opt=write&fn=" + client_comm_url + "&m=" + encodeURIComponent(JSON.stringify(data));
  var success = http_get(url);
  if (success == "0") {
    show_error("Failed to write file '" + client_comm_url + "' with message contents '" + m + "'.<br>Attempt made with url '" + url + "'.");
  }
  display_aux_message('');
}

window.send_user_action = function(t, a, m) {
  add_debug("send_user_action called");
  curr_location_img_id = m.img_id;
  var data = {type:t, action:a, message:m};
  var url = "manage_files.php?opt=write&fn=" + client_comm_url + "&m=" + encodeURIComponent(JSON.stringify(data));
  var success = http_get(url);
  if (success == "0") {
    show_error("Failed to write file '" + client_comm_url + "' with message contents '" + m + "'.<br>Attempt made with url '" + url + "'.");
  }
}

// ----------
// Navigator interface.

function show_nav() {
  add_debug("show_nav called");
  $('#user_nav_div').show();
  init_nav(scan, start_pano, end_panos, inst);
  $('#shared_instructions').text(inst);
}

function show_mirror_nav() {
  window.setOracleMode();
  $('.rating_adj').html('cooperative');
  $('.rating_verb').html('following');
  $('#user_input_message_val').html("Your partner is navigating and can ask you for directions");
  add_debug("show_mirror_nav called");
  $('#user_nav_div').show();
  $('#user_nav_end').hide();
  init_nav(scan, start_pano, end_panos, inst);
  $('#shared_instructions').text(inst);
}

function update_mirror_nav(msg) {
  update_oracle_camera(msg);
}

function enable_nav() {
  add_debug("enable_nav called");
  $('#user_nav').prop("disabled", false);
  $('#user_nav_end').prop("disabled", false);
  window.enable_nav_controls();
  $('#nav_inst').html("Try to find the goal room given the hint [left click and drag to move camera, right click blue cylinders to move]. Ask your partner for help using the chat. Your partner can see your movements on their screen.<br/>");
}

function disable_nav() {
  add_debug("disable_nav called");
  $('#user_nav').prop("disabled", true);
  $('#user_nav_end').prop("disabled", true);
  window.disable_nav_controls();
}

function send_user_end(d, uid) {
  add_debug("send_user_end called");
  var data = {type:"update", action:"end"};
  var url = "manage_files.php?opt=write&fn=" + client_comm_url + "&m=" + encodeURIComponent(JSON.stringify(data));
  var success = http_get(url);
  if (success == "0") {
    show_error("Failed to write file '" + client_comm_url + "' with message contents '" + m + "'.<br>Attempt made with url '" + url + "'.");
  }
  disable_chat();
  display_aux_message('');
}

// ----------
// Gold view interface.

function show_gold_view() {
  add_debug("show_gold_view called");
  $('#user_gold_div').show();
}

function enable_gold_view() {
  $('#user_gold').prop("disabled", false);
  $('#user_gold_play').prop("disabled", false);
  $('#skybox_gold').css({display:'block'});
  $('#user_gold_play').show();
  $('#nav_inst').html("Your partner has asked for help in the chat window! View the best next few steps by clicking \"Show Best Route\" below, and write an answer back to them.<br/>");
}

function disable_gold_view() {
  add_debug("disable_gold_view called");
  $('#user_gold').prop("disabled", true);
  $('#user_gold_play').prop("disabled", true);
  $('#skybox_gold').css({display:'none'});
  $('#user_gold_play').hide();
  window.reset_gold();
  $('#nav_inst').html("Your partner is navigating through this house. When they ask you for help you will be able to view the next few steps they should take and answer their question.<br/>");
}

function enable_exit() {
    window.onbeforeunload = null;
    $('.no_pair_message').show();
}

function exit() {
    send_user_action("exit", "exit", {});
    $('#give_up_btn').attr("disabled", "true").html("Loading...");
}

// ----------
// Misc.

// Enable the end game/get code button.
function enable_get_code(msg) {
  window.onbeforeunload = null;
  add_debug("enable_get_code called");
  $('#interaction_div').hide();
  $('#practice_div').hide();
  $('#inst_div').hide();
  $('#finished_task_div').show();
  $('#finish_task_button').show();
  $('#finish_task_button').prop("disabled", false);

  $('#finished_auxiliary_text').html($('#auxiliary_text').html());
  if ($('#finished_auxiliary_text').html() === "") {
    $('#finished_auxiliary_text').html("Thanks for participating!");
  }
  if ((msg && msg.navigator) || (msg && msg.oracle)) {
    $('#feedback_nav_id').val(msg.navigator);
    $('#feedback_oracle_id').val(msg.oracle);
    $('#helpful_rating').show();
    if (oracle_mode) {
      $('#rating_label').html("Rate the clarity of your partner's questions and how well they followed your instructions.");
    }
  } else {
    $('#helpful_rating').html("");
  }
}

// Display an auxiliary information message below the dialog interface.
function display_aux_message(msg) {
  add_debug("display_aux_message called with " + msg);
  if (msg.includes("Another player connected!")) {
    window.playSound(440.0, 'sine');
  }
  $('#auxiliary_text').html(msg);
}

// Display an error message at the bottom of the page.
function show_error(msg) {
  $('#error_text').html(msg);
}

// Display an error message at the bottom of the page.
function add_debug(msg) {
  if (debug) {
    $('#debug_text').html(msg + "<br/>" + $('#debug_text').html());    
  }
}

// Show the displayed end game message, close dialog, and open the payment button.
function end_game(msg) {
  disable_chat();
  display_aux_message(msg);
  enable_get_code();
  clearInterval(iv);

}

// All the logic for communicating with the server goes here.
function poll_for_agent_messages() {

  // Increment time so far if user is unable to respond.
  if ($('#user_say').prop("disabled")) {
    num_polls_since_last_message += 1;
  }

  // Check for communications from the server and take prescribed action.
  var contents = get_and_delete_file(server_comm_url);
  if (contents) {
    num_polls_since_last_message = 0;
    comm = JSON.parse(contents);

    var idx;
    for (idx = 0; idx < comm.length; idx++)
    {
      if (comm[idx].action == "add_chat") {
        add_chat(comm[idx].message, comm[idx].speaker);      
      }
      else if (comm[idx].action == "disable_chat") {
        disable_chat(comm[idx].timeout_at);
      }
      else if (comm[idx].action == "disable_gold_view") {
        disable_gold_view();
      }
      else if (comm[idx].action == "disable_nav") {
        disable_nav();
      }
      else if (comm[idx].action == "enable_chat") {
        enable_chat(comm[idx].timeout_at);
      }
      else if (comm[idx].action == "enable_exit") {
        enable_exit();
      }
      else if (comm[idx].action == "exit") {
        enable_get_code(comm[idx].message);
      }
      else if (comm[idx].action == "enable_gold_view") {
        enable_gold_view();
      }
      else if (comm[idx].action == "enable_nav") {
        enable_nav();
      }
      else if (comm[idx].action == "set_aux") {
        display_aux_message(comm[idx].message);
      }
      else if (comm[idx].action == "set_end_panos") {
        set_end_panos(comm[idx].value);
      }
      else if (comm[idx].action == "set_house") {
        set_house(comm[idx].value);
      }
      else if (comm[idx].action == "set_start_pano") {
        set_start_pano(comm[idx].value);
      }
      else if (comm[idx].action == "set_target_obj") {
        set_target_obj(comm[idx].value);
      }
      else if (comm[idx].action == "show_chat") {
        show_chat();
      }
      else if (comm[idx].action == "hide_instructions") {
        hide_instructions();
      }
      else if (comm[idx].action == "show_gold_view") {
        show_gold_view();
      }
      else if (comm[idx].action == "show_mirror_nav") {
        $('#practice_div').hide();
        show_mirror_nav();
      }
      else if (comm[idx].action == "show_nav") {
        $('#practice_div').hide();
        show_nav();
      }
      
      else if (comm[idx].action == "update_mirror_nav") {
        update_mirror_nav(comm[idx].message);
      }
      else {
        show_error("Unrecognized comm action " + comm[idx].action)
      }
    }
  }

  // We poll every 1 seconds (1000 ms); if polling has gone on with no messages for
  // eight minutes (internal timeouts are 7), allow ending.
  if (num_polls_since_last_message >= 480) {
    end_game("It looks like something went wrong on our end; sorry about that! You can end the HIT and recieve payment.");
  }

}

function hide_instructions() {
  $('#inst_div').hide();
  $('#interaction_div').show();
}

// Start the game.
function start_task(d, uid) {

  window.onbeforeunload = unloadListener;

  // Show display.
  $('#start_game_button').prop("disabled", true);
  //display_aux_message("Waiting on another player to connect... Please DO NOT refresh the page!");
  $('.waiting_message').show();

  // Start infinite, 5 second poll for server feedback that ends when action message is shown.
  server_comm_url = d + uid + ".server.json";
  client_comm_url = d + uid + ".client.json";

  window.send_user_action('new', '', '');
  iv = setInterval(poll_for_agent_messages, 1000);
}

function getUrlVars() {
    var vars = [], hash;
    var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
    for(var i = 0; i < hashes.length; i++)
    {
        hash = hashes[i].split('=');
        vars.push(hash[0]);
        vars[hash[0]] = decodeURIComponent(hash[1]);
    }
    return vars;
}

var urlv = getUrlVars();
if (urlv.house_scan) {
    window.scan = urlv.house_scan;
}

</script>



<script type="text/javascript" crossorigin="anonymous" src="https://cdnjs.cloudflare.com/ajax/libs/d3/4.10.2/d3.min.js"></script>
<script type="text/javascript" crossorigin="anonymous" src="https://cdnjs.cloudflare.com/ajax/libs/three.js/104/three.min.js"></script>
<script type="text/javascript" crossorigin="anonymous" src="https://cdnjs.cloudflare.com/ajax/libs/tween.js/16.3.5/Tween.min.js"></script>
<script type="text/javascript" src="<? echo(getenv("JS_PREFIX")); ?>js/RequestAnimationFrame.js"></script>
<script type="text/javascript" src="<? echo(getenv("JS_PREFIX")); ?>js/Detector.js"></script>
<script type="text/javascript" src="<? echo(getenv("JS_PREFIX")); ?>js/PTZCameraControls.js"></script>
<script type="text/javascript" src="<? echo(getenv("JS_PREFIX")); ?>js/Matterport3D.js"></script>
<script type="text/javascript" src="<? echo(getenv("JS_PREFIX")); ?>js/HIT.js?v29"></script>
<script type="text/javascript">
window.R2R_DATA_PREFIX="<? echo(getenv("R2R_DATA_PREFIX") ?: "R2R_data/"); ?>";
window.CONNECTIVITY_DATA_PREFIX="<? echo(getenv("CONNECTIVITY_DATA_PREFIX") ?: "connectivity/"); ?>";
window.MATTERPORT_DATA_PREFIX="<? echo(getenv("MATTERPORT_DATA_PREFIX") ?: "data/"); ?>";
window.MAX_GOLD_LENGTH=<? echo(getenv("MAX_GOLD_LENGTH") ?: 5); ?>;
</script>

</head>

<body onload="setup_page()" id="body_container">
<div id="container">

<?php
require_once('functions.php');

$d = 'client/';

# This is a new landing, so we need to set up the task and call the Server to make an instance.
if (!isset($_POST['uid'])) {
  $uid = uniqid();
  $client_comm_url = $d . $uid . '.client.json';

  # Show instructions.
  $inst = "<h2>INSTRUCTIONS</h2><br/>";
  ?>
  <div class="row" id="inst_div">
    <div class="col-md-12">
        <p style="color:#00f;font-size: 18px;line-height:40px;display:none;" class="waiting_message" >Waiting on another player to connect... Please DO NOT refresh the page!</p>

        <div style="display:none;" class="no_pair_message" id="no_pair_message">
            <div class="alert alert-warning">
            <p>Looks like there's no one around to pair with! Sorry about that. If you don't want to wait any longer you can end the HIT and receive payment.</p>
            </div>

            <button onclick="exit()" style="clear:both;" id="give_up_btn" class="btn btn-danger">Give up and skip to survey</button>
        </div>
      <?php echo $inst;?>
      <div id="instructions_content">
      <p>
        We are researchers collecting information about how people help one another navigate using language.
        In this HIT, you will be paired with a partner.
        <b>You will collaborate to reach a goal room within a house.</b>
        One person will be the <b>navigator</b>: walking around the house trying to find the room.
        The other will be the <b>oracle</b>: answering questions about where to go next.
      </p>
      <p><b>The goal room won’t be specified exactly</b>, for example, "Find the room with a plant."
        There can be lots of plants in a house!
        Figuring out <i>which</i> room in the house is the challenge, and will require <i>both</i> players to solve.
        The oracle can view the next few steps the navigator should take, enabling them to give guidance.
      </p>

        <div class="show" id="collapseExample">


      <h3>Partner 1: Navigator</h3>
      <p>The navigator will be dropped into a house and given an hint of which room they must find (e.g., "Find the room with the plant.").
      The navigator can move through the house with the following mouse controls:</p>

      <h4>Mouse Controls:</h4>

        <ul>
        <li><strong>Left-click and drag the image</strong> to look around.</li>
        <li><strong>Right-click on a blue cylinder</strong> to move to that position (note: sometimes the blue cylinders are close to your feet, so you may need to look down).</li>
       </ul>


<p class="practice_instructions">Please practice navigation below, and <b>return this HIT if you are unable to move the camera [left click and drag] and move around [right click on blue cylinders].</b>
<button type="button" class="btn btn-primary" data-toggle="modal" data-target="#practice_modal" style="margin-bottom:10px">
  Click here to practice navigation
</button>
</p>



      <p>The target room can be far away from the starting pint, so the hint alone will not be enough.
      The navigator should communicate with their oracle partner using the chat interface.
      The oracle is provided with a preview of the next best steps towards the room so they can answer questions to guide the navigator.
      </p>

      <p>
      <b>When the navigator sends a question to the oracle, navigation will pause until the oracle sends a response!</b>
      The navigator should ask the oracle specific questions, for example:
    </p>

      <div class="row">
          <!--<div class="col-md-3"><img src="img/nav_example_1.png" width="100%" /></div>-->
          <div class="col-md-12">
            <p class="alert alert-success"><i class="glyphicon glyphicon-ok"></i> <strong>GOOD Question:</strong>&nbsp;"Should I go through the door to my left or towards the sofa to my right?"&nbsp;<strong>(specific + detailed)</strong></p>
            <p class="alert alert-danger"><i class="glyphicon glyphicon-remove"></i> <strong>BAD Question:</strong>&nbsp;"Where now?"&nbsp;<strong>(unspecific + unhelpful)</strong></p>
          </div>
        </div>
<br/>

      <p>After asking a question, the scene will pause until the oracle responds. Then, the navigator can continue moving throughout the scene.</p>

      <p>When the navigator thinks they have located the room, they will click the "<i>Guess This Room</i>" button. If correct, the task will end. Otherwise, the navigator will have to ask the oracle for help.</p>

      <h3>Partner 2: Oracle</h3>

      <p>The oracle observes as the navigator moves through the house.
      When the navigator asks a question, the oracle is provided with a preview of the best next steps to take toward the goal room.
      It is the oracle's job to describe these steps to the navigator by sending a response in the chat.
      Before responding, they can replay the next best steps as many times as they want by clicking the "<i>Show Best Route</i>" button.</p>

      <p><b>When the oracle sends a response to the navigator, they will again observe the navigator moving through the house!</b>
        When describing the best path, the oracle should be as helpful as possible, for example:

         <div class="row">
          <!--<div class="col-md-3"><img src="img/nav_example_1.png" width="100%" /></div>-->
          <div class="col-md-12">
            <p class="alert alert-success"><i class="glyphicon glyphicon-ok"></i> <strong>GOOD Response:</strong>&nbsp;"Move through the door, then turn left and go down the hall towards the staircase."&nbsp;<strong>(specific + detailed)</p>
            <p class="alert alert-danger"><i class="glyphicon glyphicon-remove"></i> <strong>BAD Response:</strong>&nbsp;"Go left."&nbsp;<strong>(short + lacks details)</p>
          </div>
        </div>

</div>
</div>

<button style="float:left;" class="btn btn-success btn-lg" id="start_game_button" onclick="start_task('<?php echo $d;?>', '<?php echo $uid;?>')">Start task</button>
<p style="color:#00f;float:left; margin-left: 10px;font-size: 18px;line-height:40px;display:none;" class="waiting_message" >Waiting on another player to connect... Please DO NOT refresh the page!</p>


    </div>
  </div>
  <?php
}
?>

<div id="interaction_div" style="display:none;">
<div class="alert alert-warning" style="display:block;">
 <p>Do not navigate away from this page until the task is complete!</p>
 <p style="font-size:12px">Closing or reloading this tab may prevent you or other players from successfully completing this HIT!
If you have any problems, please email us instead at <a style="background:none;padding:0;margin:0;color:#8a6d3b;text-decoration:underline;font-size:13px" href="mailto:mp-dialog@cs.washington.edu">mp-dialog@cs.washington.edu</a></p>
</div>
  <div class="row">
    <div class="col-md-6">
      <div id="user_nav_div" style="display:none;">
        <figure style="display: inline-block; width: 100%;"><canvas id="skybox" style="width:100%; height:auto; display: block; margin: 0 auto;"> </canvas></figure>
        <p id="nav_inst">
        </p>
        <p>
          <button class="btn btn-success" disabled id="user_nav_end" onclick="send_user_stop('<?php echo $d;?>', '<?php echo $uid;?>')"><b>Guess This Room</b><br/>
          <div style="font-size:13px">If you are incorrect, you will have to ask your partner a question.</div></button>
        </p>
      </div>
      <div id="user_gold_div" style="display:none;">
        <figure style="display: inline-block; width: 100%;"><canvas id="skybox_gold" style="width:100%; height:auto; display: none; margin: 0 auto;"> </canvas></figure>
        <p>
          <button class="btn" style="display:none;" disabled="disabled" id="user_gold_play" onclick="window.play_animation()"><b>Show Best Route</b><br/>
          <div style="color:#00f;font-size:13px">If no route is shown when you click, then your partner is in the goal room.</div></button>
        </p>
      </div>
    </div>
    <div class="col-md-6">
      <div id="dialog_div" style="display:none;">
        <p id="shared_instructions"></p>
        <p>
            <button type="button" class="btn btn-primary" data-toggle="modal" data-target="#reviewInstModal">
  Review full instructions
</button>

<!-- Modal -->
<div class="modal fade" id="reviewInstModal" tabindex="-1" role="dialog" aria-labelledby="reviewInstModalLabel">
  <div class="modal-dialog modal-lg" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h4 class="modal-title" id="reviewInstModalLabel">Instructions</h4>
      </div>
      <div class="modal-body" id="reviewInstBody">

      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
      </div>
    </div>
  </div>
</div>
        </p>
        <table id="dialog_table" class="dialog_table">
          <thead><th class="chat_header_row">You
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        Partner</th></thead>
          <tbody></tbody>
        </table>
        <p>
          <input type="text" disabled id="user_input" style="width:100%;" placeholder="your message..." onkeydown="if (event.keyCode == 13) {$('#user_say').click();}"><br/>
          <button class="btn" disabled id="user_say" onclick="send_user_chat('<?php echo $d;?>', '<?php echo $uid;?>')" style="margin-top:5px;margin-bottom:10px;">Send Message and Change Turns</button>
          <div style="color:#00f;font-size:13px;" id="user_input_message"><span id="user_input_message_val">Your partner is viewing your next best steps and answering your question</span>...</div>
        </p>
        <p>
            <div id="time_left" style="color:#00f;font-size:13px">(<span id="time_left_label">Your partner has</span>&nbsp;<span id="time_left_value"></span> to chat.)</div>
        </p>
      </div>
    </div>
  </div>
  <div class="row">
    <div class="col-md-12">
      <p id="auxiliary_text" style="color:blue"></p>
    </div>
  </div>
  <div class="row">
    <div class="col-md-12">
      <p id="error_text" style="color:red"></p>
    </div>
  </div>
  <div class="row">
    <div class="col-md-12">
      <p id="debug_text" style="color:purple;display:none;"></p>
    </div>
  </div>
  <div class="row">
    <div class="col-md-12">
        <div style="display:none;" class="no_pair_message">
            <button onclick="exit()" style="clear:both;" id="give_up_btn" class="btn btn-danger">Give up and skip to survey</button>
        </div>
    </div>
   </div>
</div>

<div id="practice_div" style="display:none;">
<button type="button" class="btn btn-primary" data-toggle="modal" data-target="#practice_modal" style="margin-bottom:10px">
  Click here to practice navigation
</button>

<!-- Modal -->
</div>

<div class="modal fade" id="practice_modal" tabindex="-1" role="dialog" aria-labelledby="myModalLabel">
  <div class="modal-dialog" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h4 class="modal-title" id="myModalLabel">Practice Navigation</h4>
      </div>
      <div class="modal-body">
                <figure style="display: inline-block; width: 100%;"><canvas id="skybox_demo" style="width:100%; height:auto; display: block; margin: 0 auto;"> </canvas></figure>

      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-default" data-dismiss="modal">Done</button>
      </div>
    </div>
  </div>
</div>

<div id="finished_task_div" style="display:none;">
  <div class="row">
    <div class="col-md-12">
       <div class="alert alert-success" role="alert" id="finished_auxiliary_text"></div>
      <form action="generate_code.php" method="POST">
      <div class="form-group" id="helpful_rating" style="display:none;">
        <label for="rating">How helpful was your partner?</label>
        <p id="rating_label">Rate the helpfulness of your partner in answering your questions and helping you get to the goal.</p>
        <div class="radio">
          <label>
            <input required type="radio" name="rating" id="rating" value="1">
            1 - Partner was not <span class="rating_adj">helpful</span>
          </label>
        </div>
        <div class="radio">
          <label>
            <input required type="radio" name="rating" id="rating" value="2" >
            2 - Partner was not great at <span class="rating_verb">giving</span> instructions
          </label>
        </div>
        <div class="radio">
          <label>
            <input required type="radio" name="rating" id="rating" value="3" >
            3 - Partner was okay at <span class="rating_verb">giving</span> instructions
          </label>
        </div>
        <div class="radio">
          <label>
            <input required type="radio" name="rating" id="rating" value="4" >
            4 - Partner was pretty <span class="rating_adj">helpful</span>
          </label>
        </div>
        <div class="radio">
          <label>
            <input required type="radio" name="rating" id="rating" value="5" >
            5 - Partner was really <span class="rating_adj">helpful</span>
          </label>
        </div>
      </div>
      <div class="form-group">
        <input type="checkbox" name="problem" value="true"> Check this box if you experienced technical errors in your HIT (e.g., navigation stopped working, oracle was unable to view steps, etc.).
      </div>
      <div class="form-group">
        <label for="free_form_feedback">Please provide any additional feedback you have:</label>
        <textarea class="form-control" rows="3" name="free_form_feedback" id="free_form_feedback"></textarea>
      </div>

      <p>Click the button below to submit your feedback and generate your Mechanical Turk code needed to submit the HIT.</p>


        <input type="hidden" name="uid" value="<?php echo $uid;?>">
        <input type="hidden" name="navigator" id="feedback_nav_id" value="">
        <input type="hidden" name="oracle" id="feedback_oracle_id" value="">
        <input type="submit" class="btn btn-default" id="finish_task_button" value="Get Mechanical Turk code" style="display:none;" disabled>
      </form>
    </div>
  </div>
</div>

</div>

</body>

<script type="text/javascript">

demo_skybox_init();
demo_load_connections();

var urlv = getUrlVars();
if (urlv.house_scan && urlv.start_pano && urlv.end_panos && urlv.inst) {
    window.setDebugMode();
    if (urlv.mode == "oracle") {
        window.setOracleMode();
    }
    $('#inst_div').hide();
      $('#start_game_button').prop("disabled", true);
      $('#interaction_div').show();
    $('#user_nav_div').show();
    show_chat();
    init_nav(urlv.house_scan, urlv.start_pano, urlv.end_panos.split(","), urlv.inst);
    $('#shared_instructions').text(urlv.inst);
    if (urlv.mode == "oracle") {
        show_gold_view();
        enable_gold_view();
        var idx;
        var goal_image_ids = urlv.end_panos.split(",");
         var optimal_policies = Array(goal_image_ids.length);
          for (idx = 0; idx < goal_image_ids.length; idx++) {
            load_optimal_policy(idx);
          }
    }
}

if (urlv.max_gold_len) {
    window.MAX_GOLD_LENGTH = parseInt(urlv.max_gold_len);
}

$('#reviewInstBody').html($('#instructions_content').clone().css({fontWeight:'normal', fontSize:'14px'}));
$('#reviewInstBody').find('.practice_instructions').remove();

</script>

</html>
