
var scan= window.scan || "sT4fr6TAbpF";
var curr_image_id;
var curr_image_id_gold;
var curr_image_id_demo;
var goal_image_ids;

// declare a bunch of variable we will need later
var camera, camera_pose, scene, controls, renderer, connections, id_to_ix, world_frame, cylinder_frame, cubemap_frame;
var camera_gold, camera_pose_gold, scene_gold, controls_gold, renderer_gold,
    world_frame_gold, cylinder_frame_gold, cubemap_frame_gold;
var mouse = new THREE.Vector2();
var id, id_gold, last_pose;

var SIZE_X = 960;
var SIZE_Y = 540;
var VFOV = 90;
var ASPECT = SIZE_X/SIZE_Y;
var path;
var oracle_mode = false;
var playing = false;
var optimal_policies;
var shortest_policy;
var reversed_policies = {};
var debug_mode = false;


var camera_demo, camera_pose_demo, scene_demo, controls_demo, renderer_demo, connections_demo, id_to_ix_demo, world_frame_demo, cylinder_frame_demo, cubemap_frame_demo;

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

window.setOracleMode = function() {
  oracle_mode = true;
  window.oracle_mode = true;
  gold_skybox_init();
  $('#nav_inst').html("Your partner is navigating through this house. When they ask you for help you will be able to view the next few steps they should take and answer their question.<br/>");
};

window.setDebugMode = function() {
  window.send_user_action = function() {  };
  debug_mode = true;
};

var matt = new Matterport3D("");

window.init_nav = function(house_scan, start_pano, end_panos, inst) {
  console.log("?house_scan="+encodeURIComponent(house_scan)+
      "&start_pano="+encodeURIComponent(start_pano)+
      "&end_panos="+encodeURIComponent(end_panos)+"&inst="+encodeURIComponent(inst));
  matt.loadJson(window.R2R_DATA_PREFIX + '/R2R_train.json').then(function(data){
    scan = house_scan;
    curr_image_id = start_pano;
    curr_image_id_gold = start_pano;
    goal_image_ids = end_panos;
    $('#instr').text(inst);
    skybox_init();
    load_connections(scan, curr_image_id);

    if (oracle_mode) {
      var idx;
      optimal_policies = Array(goal_image_ids.length);
      for (idx = 0; idx < goal_image_ids.length; idx++) {
        load_optimal_policy(idx);
      }
    }
  });
};

window.disable_nav_controls = function() {
  controls.enabled=false;
  $('#skybox').css({'opacity': 0.5});
};

window.enable_nav_controls = function() {
  if (!controls) return; // Not initialized yet, just return...
  controls.enabled=true;
  $('#skybox').css({'opacity': 1.0});
};

window.update_oracle_camera = function(msg, gold_only = false) {
  if (!controls) {
    return;
  }

  function animateCylinderTransition(cylinder_frame, camera, camera_pose, renderer, scene, world_frame, is_gold) {
      var cylinder = cylinder_frame.getObjectByName(msg.img_id);
      if (cylinder) {
        cylinder.currentHex = cylinder.material.emissive.getHex();
        cylinder.material.emissive.setHex(0xff0000);
        setTimeout(function () {
          cylinder.material.emissive.setHex(cylinder.currentHex);
        }, 200);
        if (is_gold && playing) {
          take_action(msg.img_id, cylinder_frame, camera, camera_pose, renderer, scene, world_frame, is_gold);
        } else {
          take_action_no_anim(msg.img_id, cylinder_frame, camera, camera_pose, renderer, scene, world_frame, is_gold);
        }
      }
    }

  if (msg.img_id != curr_image_id && !gold_only) {
    animateCylinderTransition(cylinder_frame, camera, camera_pose, renderer, scene, world_frame);
  }
  if (msg.img_id != curr_image_id_gold && (gold_only || !playing)) {
    animateCylinderTransition(cylinder_frame_gold, camera_gold, camera_pose_gold, renderer_gold, scene_gold, world_frame_gold, true);
  }

  if (msg.rot) {
    controls.camera.rotation.x = msg.rot._x;
    controls.camera.rotation.y = msg.rot._y;
    render(renderer, scene, camera);

    if (!playing) {
      controls_gold.camera.rotation.x = msg.rot._x;
      controls_gold.camera.rotation.y = msg.rot._y;
      render(renderer_gold, scene_gold, camera_gold);
    }
  }
};

function load_optimal_policy(idx) {
  matt.loadJson(window.MATTERPORT_DATA_PREFIX + '/v1/scans/'+scan+'/policies/'+goal_image_ids[idx]+'.json').then(function(policyData){
    optimal_policies[idx] = policyData;
    reversed_policies = {};
    $('#user_gold_play').removeAttr('disabled');
  });
}

function readTextFile(file)
{
    var rawFile = new XMLHttpRequest();
    rawFile.open("GET", file, false);
    rawFile.onreadystatechange = function ()
    {
        if(rawFile.readyState === 4)
        {
            if(rawFile.status === 200 || rawFile.status == 0)
            {
                var allText = rawFile.responseText;
                alert(allText);
            }
        }
    }
    rawFile.send(null);
}

// ## Initialize everything
function skybox_init() {
  // test if webgl is supported
  if (! Detector.webgl) Detector.addGetWebGLMessage();

  // create the camera (kinect 2)
  camera = new THREE.PerspectiveCamera(VFOV, ASPECT, 0.01, 1000);
  camera_pose = new THREE.Group();
  camera_pose.add(camera);
  
  // create the Matterport world frame
  world_frame = new THREE.Group();
  
  // create the cubemap frame
  cubemap_frame = new THREE.Group();
  cubemap_frame.rotation.x = -Math.PI; // Adjust cubemap for z up
  cubemap_frame.add(world_frame);
  
  // create the Scene
  scene = new THREE.Scene();
  world_frame.add(camera_pose);
  scene.add(cubemap_frame);

  var light = new THREE.DirectionalLight( 0xFFFFFF, 1 );
  light.position.set(0, 0, 100);
  world_frame.add(light);
  world_frame.add(new THREE.AmbientLight( 0xAAAAAA )); // soft light

  // init the WebGL renderer
  renderer = new THREE.WebGLRenderer({canvas: document.getElementById("skybox"), antialias: true } );
  renderer.setSize(SIZE_X, SIZE_Y);


  controls = new THREE.PTZCameraControls(camera, renderer.domElement);
  controls.minZoom = 1;
  controls.maxZoom = 3.0;
  controls.minTilt = -0.6 * Math.PI / 2;
  controls.maxTilt = 0.6 * Math.PI / 2;
  controls.enableDamping = true;
  controls.panSpeed = -0.25;
  controls.tiltSpeed = -0.25;
  controls.zoomSpeed = 1.5;
  controls.dampingFactor = 0.5;

  controls.addEventListener('select', select);
  controls.addEventListener('change', function() { render(renderer, scene, camera); });
  controls.addEventListener('rotate', log_pose);
  if (oracle_mode) {
    controls.enabled=false;
    controls.dispose();
  }
}

function gold_skybox_init() {
  // create the camera (kinect 2)
  camera_gold = new THREE.PerspectiveCamera(VFOV, ASPECT, 0.01, 1000);
  camera_pose_gold = new THREE.Group();
  camera_pose_gold.add(camera_gold);

  // create the Matterport world frame
  world_frame_gold = new THREE.Group();

  // create the cubemap frame
  cubemap_frame_gold = new THREE.Group();
  cubemap_frame_gold.rotation.x = -Math.PI; // Adjust cubemap for z up
  cubemap_frame_gold.add(world_frame_gold);

  // create the Scene
  scene_gold = new THREE.Scene();
  world_frame_gold.add(camera_pose_gold);
  scene_gold.add(cubemap_frame_gold);

  var light_gold = new THREE.DirectionalLight( 0xFFFFFF, 1 );
  light_gold.position.set(0, 0, 100);
  world_frame_gold.add(light_gold);
  world_frame_gold.add(new THREE.AmbientLight( 0xAAAAAA )); // soft light

  // init the WebGL renderer
  renderer_gold = new THREE.WebGLRenderer({canvas: document.getElementById("skybox_gold"), antialias: true } );
  renderer_gold.setSize(SIZE_X, SIZE_Y);


  controls_gold = new THREE.PTZCameraControls(camera_gold, renderer_gold.domElement);
  controls_gold.minZoom = 1;
  controls_gold.maxZoom = 3.0;
  controls_gold.minTilt = -0.6 * Math.PI / 2;
  controls_gold.maxTilt = 0.6 * Math.PI / 2;
  controls_gold.enableDamping = true;
  controls_gold.panSpeed = -0.25;
  controls_gold.tiltSpeed = -0.25;
  controls_gold.zoomSpeed = 1.5;
  controls_gold.dampingFactor = 0.5;

  controls_gold.dispose();
}

function demo_skybox_init() {
  // test if webgl is supported
  if (! Detector.webgl) Detector.addGetWebGLMessage();

  // create the camera (kinect 2)
  camera_demo = new THREE.PerspectiveCamera(VFOV, ASPECT, 0.01, 1000);
  camera_pose_demo = new THREE.Group();
  camera_pose_demo.add(camera_demo);

  // create the Matterport world frame
  world_frame_demo = new THREE.Group();

  // create the cubemap frame
  cubemap_frame_demo = new THREE.Group();
  cubemap_frame_demo.rotation.x = -Math.PI; // Adjust cubemap for z up
  cubemap_frame_demo.add(world_frame_demo);

  // create the Scene
  scene_demo = new THREE.Scene();
  world_frame_demo.add(camera_pose_demo);
  scene_demo.add(cubemap_frame_demo);

  var light_demo = new THREE.DirectionalLight( 0xFFFFFF, 1 );
  light_demo.position.set(0, 0, 100);
  world_frame_demo.add(light_demo);
  world_frame_demo.add(new THREE.AmbientLight( 0xAAAAAA )); // soft light

  // init the WebGL renderer
  renderer_demo = new THREE.WebGLRenderer({canvas: document.getElementById("skybox_demo"), antialias: true } );
  renderer_demo.setSize(SIZE_X, SIZE_Y);


  controls_demo = new THREE.PTZCameraControls(camera_demo, renderer_demo.domElement);
  controls_demo.minZoom = 1;
  controls_demo.maxZoom = 3.0;
  controls_demo.minTilt = -0.6 * Math.PI / 2;
  controls_demo.maxTilt = 0.6 * Math.PI / 2;
  controls_demo.enableDamping = true;
  controls_demo.panSpeed = -0.25;
  controls_demo.tiltSpeed = -0.25;
  controls_demo.zoomSpeed = 1.5;
  controls_demo.dampingFactor = 0.5;

  controls_demo.addEventListener('select', select_demo);
  controls_demo.addEventListener('change', function() { render(renderer_demo, scene_demo, camera_demo); });
}

function gold_skybox_reinit() {

  camera_gold = camera.clone(true);

  camera_pose_gold = camera_pose.clone(true);
  camera_pose_gold.remove(camera_pose_gold.children[0]);
  camera_pose_gold.add(camera_gold);

  world_frame_gold = world_frame.clone(true);
  for (var child in world_frame_gold.children) {
    world_frame_gold.remove(child);
  }

  cubemap_frame_gold = cubemap_frame.clone(true);
  cubemap_frame_gold.remove(cubemap_frame_gold.children[0]);
  cubemap_frame_gold.add(world_frame_gold);

  scene_gold = scene.clone(true);
  world_frame_gold.add(camera_pose_gold);
  scene_gold.add(cubemap_frame_gold);

  var light_gold = new THREE.DirectionalLight( 0xFFFFFF, 1 );
  light_gold.position.set(0, 0, 100);
  world_frame_gold.add(light_gold);
  world_frame_gold.add(new THREE.AmbientLight( 0xAAAAAA )); // soft light

  controls_gold.camera = camera_gold;
}

function select(event) {
  var mouse = new THREE.Vector2();
  var raycaster = new THREE.Raycaster();
  var x = renderer.domElement.offsetWidth;
  var y = renderer.domElement.offsetHeight;
  mouse.x = ( event.x / x ) * 2 - 1;
  mouse.y = - ( event.y / y ) * 2 + 1;
  raycaster.setFromCamera( mouse, camera );
  var intersects = raycaster.intersectObjects( cylinder_frame.children );
  if ( intersects.length > 0 ) {
    intersects[0].object.currentHex = intersects[0].object.material.emissive.getHex();
    intersects[0].object.material.emissive.setHex( 0xff0000 );
    image_id = intersects[ 0 ].object.name;
    take_action(image_id, cylinder_frame, camera, camera_pose, renderer, scene, world_frame);
    setTimeout(function(){ intersects[0].object.material.emissive.setHex( intersects[0].object.currentHex ); }, 200);
  }
}

function select_demo(event) {
  var mouse = new THREE.Vector2();
  var raycaster = new THREE.Raycaster();
  var x = renderer_demo.domElement.offsetWidth;
  var y = renderer_demo.domElement.offsetHeight;
  mouse.x = ( event.x / x ) * 2 - 1;
  mouse.y = - ( event.y / y ) * 2 + 1;
  raycaster.setFromCamera( mouse, camera_demo );
  var intersects = raycaster.intersectObjects( cylinder_frame_demo.children );
  if ( intersects.length > 0 ) {
    intersects[0].object.currentHex = intersects[0].object.material.emissive.getHex();
    intersects[0].object.material.emissive.setHex( 0xff0000 );
    image_id = intersects[ 0 ].object.name;
    take_action_demo(image_id, cylinder_frame_demo, camera_demo, camera_pose_demo, renderer_demo, scene_demo, world_frame_demo);
    setTimeout(function(){ intersects[0].object.material.emissive.setHex( intersects[0].object.currentHex ); }, 200);
  }
}


function initialize_data(scan, image_id, gold_only=false) {
  // Create a cylinder frame for showing arrows of directions
  if (!gold_only) cylinder_frame = matt.load_viewpoints(connections);
  cylinder_frame_gold = matt.load_viewpoints(connections);

  if (oracle_mode) {
    cylinder_frame.visible = false;
    cylinder_frame_gold.visible = false;
  }

  // Keep a structure of connection graph
  id_to_ix = {};
  for (var i = 0; i < connections.length; i++) {
    var im = connections[i]['image_id'];
    id_to_ix[im] = i;
  }

  if (!gold_only) world_frame.add(cylinder_frame);
  if (world_frame_gold) {
    world_frame_gold.add(cylinder_frame_gold);
  }
  matt.loadCubeTexture(cube_urls(scan, image_id)).then(function(texture){

    if (!gold_only) scene.background = texture;

    if (scene_gold) {
      scene_gold.background = texture;
    }

    if (!gold_only) move_to(image_id, cylinder_frame, world_frame, true);
    if (cylinder_frame_gold && world_frame_gold) {
      move_to(image_id, cylinder_frame_gold, world_frame_gold, true, true);
    }
  });
}


function initialize_data_demo() {
  // Create a cylinder frame for showing arrows of directions
  cylinder_frame_demo = matt.load_viewpoints(connections_demo);

  // Keep a structure of connection graph
  id_to_ix_demo = {};
  for (var i = 0; i < connections_demo.length; i++) {
    var im = connections_demo[i]['image_id'];
    id_to_ix_demo[im] = i;
  }


  world_frame_demo.add(cylinder_frame_demo);
  matt.loadCubeTexture(cube_urls("sT4fr6TAbpF", "976ad0993bce4c5784da72eb4570d795")).then(function(texture){

    scene_demo.background = texture;

    move_to_demo("976ad0993bce4c5784da72eb4570d795", true);
  });
}

function reinitialize_data(scan, image_id) {
  // Create a cylinder frame for showing arrows of directions
  if (world_frame_gold) {
    world_frame_gold.add(cylinder_frame_gold);
  }
  scene_gold.background = scene.background;
  move_to(image_id, cylinder_frame_gold, world_frame_gold, true, true);
}

function load_connections(scan, image_id) {
  if (!connections) {
    var pose_url = window.CONNECTIVITY_DATA_PREFIX + "/" + scan + "_connectivity.json";
    d3.json(pose_url, function (error, data) {
      if (error) return console.warn(error);
      connections = data;
      initialize_data(scan, image_id);
    });
  } else {
    initialize_data(scan, image_id);
  }
}

function demo_load_connections() {
  if (!connections_demo) {
    var pose_url = window.CONNECTIVITY_DATA_PREFIX + "/sT4fr6TAbpF_connectivity.json";
    d3.json(pose_url, function(error, data) {
      if (error) return console.warn(error);
      connections_demo = data;
      initialize_data_demo();
    })
  }
}

function cube_urls(scan, image_id) {
  var urlPrefix  = window.MATTERPORT_DATA_PREFIX + "/v1/scans/" + scan + "/matterport_skybox_images/" + image_id;
  return [ urlPrefix + "_skybox2_sami.jpg", urlPrefix + "_skybox4_sami.jpg",
      urlPrefix + "_skybox0_sami.jpg", urlPrefix + "_skybox5_sami.jpg",
      urlPrefix + "_skybox1_sami.jpg", urlPrefix + "_skybox3_sami.jpg" ];
}

function move_to(image_id, cylinder_frame, world_frame, isInitial=false, isGold=false) {
  // Adjust cylinder visibility
  var cylinders = cylinder_frame.children;
  for (var i = 0; i < cylinders.length; ++i){
    cylinders[i].visible = isGold && playing ? false : connections[id_to_ix[image_id]]['unobstructed'][i] && cylinders[i].included;
  }
  // Correct world frame for individual skybox camera rotation
  var inv = new THREE.Matrix4();
  var cam_pose = cylinder_frame.getObjectByName(image_id);

  inv.getInverse(cam_pose.matrix);
  var ignore = new THREE.Vector3();
  inv.decompose(ignore, world_frame.quaternion, world_frame.scale);
  world_frame.updateMatrix();
  if (!isGold) {
    if (isInitial) {
      set_camera_pose(camera_pose, cam_pose.matrix, cam_pose.height);
    } else {
      set_camera_position(camera_pose, cam_pose.matrix, cam_pose.height);
    }
    render(renderer, scene, camera);
  } else{
    if (isInitial){
      set_camera_pose(camera_pose_gold, cam_pose.matrix, cam_pose.height);
    } else {
      set_camera_position(camera_pose_gold, cam_pose.matrix, cam_pose.height);
    }
    render(renderer_gold, scene_gold, camera_gold);
  }
  if (isGold) {
    curr_image_id_gold = image_id;
  }else {
    curr_image_id = image_id;
  }
  log_pose();

  // Animation
  if (playing) {
    step_forward();
  }
}

function move_to_demo(image_id, isInitial=false, isGold=false) {
  // Adjust cylinder visibility
  var cylinders = cylinder_frame_demo.children;
  for (var i = 0; i < cylinders.length; ++i){
    cylinders[i].visible = connections_demo[id_to_ix_demo[image_id]]['unobstructed'][i] && cylinders[i].included;
  }
  // Correct world frame for individual skybox camera rotation
  var inv = new THREE.Matrix4();
  var cam_pose = cylinder_frame_demo.getObjectByName(image_id);

  inv.getInverse(cam_pose.matrix);
  var ignore = new THREE.Vector3();
  inv.decompose(ignore, world_frame_demo.quaternion, world_frame_demo.scale);
  world_frame_demo.updateMatrix();

    if (isInitial) {
      set_camera_pose(camera_pose_demo, cam_pose.matrix, cam_pose.height);
    } else {
      set_camera_position(camera_pose_demo, cam_pose.matrix, cam_pose.height);
    }
    render(renderer_demo, scene_demo, camera_demo);

  curr_image_id_demo = image_id;

}

function set_camera_pose(camera_pose, matrix4d, height){
  matrix4d.decompose(camera_pose.position, camera_pose.quaternion, camera_pose.scale);
  camera_pose.position.z += height;
  camera_pose.rotateX(Math.PI); // convert matterport camera to webgl camera
}

function set_camera_position(camera_pose, matrix4d, height) {
  var ignore_q = new THREE.Quaternion();
  var ignore_s = new THREE.Vector3();
  matrix4d.decompose(camera_pose.position, ignore_q, ignore_s);
  camera_pose.position.z += height;
}

function get_camera_pose(camera, camera_pose){
  camera.updateMatrix();
  camera_pose.updateMatrix();
  var m = camera.matrix.clone();
  m.premultiply(camera_pose.matrix);
  return m;
}

Math.degrees = function(radians) {
  return radians * 180 / Math.PI;
};

function log_pose() {
  var pose = get_pose();
  var pose_str = JSON.stringify(pose);
  if (pose_str !== last_pose) {
    if (!oracle_mode) window.send_user_action("update", "nav", pose);
    last_pose = pose_str;
  }
}

function get_pose() {
  return {
    rot: camera.rotation,
    pos: camera.position,
    img_id: curr_image_id
  };
}


function take_action_no_anim(image_id, cylinder_frame, camera, camera_pose, renderer, scene, world_frame, isGold) {
  var texture_promise = matt.loadCubeTexture(cube_urls(scan, image_id)); // start fetching textures
  var target = cylinder_frame.getObjectByName(image_id);

  // Camera up vector
  var camera_up = new THREE.Vector3(0,1,0);
  var camera_look = new THREE.Vector3(0,0,-1);
  var camera_m = get_camera_pose(camera, camera_pose);
  var zero = new THREE.Vector3(0,0,0);
  camera_m.setPosition(zero);
  camera_up.applyMatrix4(camera_m);
  camera_up.normalize();
  camera_look.applyMatrix4(camera_m);
  camera_look.normalize();

  // look direction
  var look = target.position.clone();
  look.sub(camera_pose.position);
  look.projectOnPlane(camera_up);
  look.normalize();
  // Simplified - assumes z is zero
  var rotate = Math.atan2(look.y,look.x) - Math.atan2(camera_look.y,camera_look.x);
  if (rotate < -Math.PI) rotate += 2*Math.PI;
  if (rotate > Math.PI) rotate -= 2*Math.PI;

  var target_y = camera.rotation.y + rotate;

  // camera.rotation.x = camera.rotation.x,
  camera.rotation.y = target_y;
  camera.rotation.z = 0;

  render(renderer, scene, camera);
  // var new_vfov = VFOV*0.95;
  // var zoom_tween = new TWEEN.Tween({
  //   vfov: VFOV})
  // .to( {vfov: new_vfov }, 500 )
  // .easing(TWEEN.Easing.Cubic.InOut)
  // .onUpdate(function() {
  //   camera.fov = this.vfov;
  //   camera.updateProjectionMatrix();
  //   render(renderer, scene, camera);
  // })
  // .onComplete(function(){
  //   cancelAnimationFrame(isGold ? id_gold : id);
    // cancelAnimationFrame(id);
  texture_promise.then(function(texture) {
    scene.background = texture;
    camera.fov = VFOV;
    camera.updateProjectionMatrix();

    move_to(image_id, cylinder_frame, world_frame, false, isGold)
  });
  // });
}

function take_action(image_id, cylinder_frame, camera, camera_pose, renderer, scene, world_frame, isGold) {
  var texture_promise = matt.loadCubeTexture(cube_urls(scan, image_id)); // start fetching textures
  var target = cylinder_frame.getObjectByName(image_id);

  // Camera up vector
  var camera_up = new THREE.Vector3(0,1,0);
  var camera_look = new THREE.Vector3(0,0,-1);
  var camera_m = get_camera_pose(camera, camera_pose);
  var zero = new THREE.Vector3(0,0,0);
  camera_m.setPosition(zero);
  camera_up.applyMatrix4(camera_m);
  camera_up.normalize();
  camera_look.applyMatrix4(camera_m);
  camera_look.normalize();

  // look direction
  var look = target.position.clone();
  look.sub(camera_pose.position);
  look.projectOnPlane(camera_up);
  look.normalize();
  // Simplified - assumes z is zero
  var rotate = Math.atan2(look.y,look.x) - Math.atan2(camera_look.y,camera_look.x);
  if (rotate < -Math.PI) rotate += 2*Math.PI;
  if (rotate > Math.PI) rotate -= 2*Math.PI;

  var target_y = camera.rotation.y + rotate;
  var rotate_tween = new TWEEN.Tween({
    x: camera.rotation.x,
    y: camera.rotation.y,
    z: camera.rotation.z})
  .to( {
    x: camera.rotation.x,
    y: target_y,
    z: 0 }, 2000*Math.abs(rotate) )
  .easing( TWEEN.Easing.Cubic.InOut)
  .onUpdate(function() {
    camera.rotation.x = this.x;
    camera.rotation.y = this.y;
    camera.rotation.z = this.z;

    // camera.updateProjectionMatrix();

    render(renderer, scene, camera);
  });
  var new_vfov = VFOV*0.95;
  var zoom_tween = new TWEEN.Tween({
    vfov: VFOV})
  .to( {vfov: new_vfov }, 500 )
  .easing(TWEEN.Easing.Cubic.InOut)
  .onUpdate(function() {
    camera.fov = this.vfov;
    camera.updateProjectionMatrix();
    render(renderer, scene, camera);
  })
  .onComplete(function(){
    cancelAnimationFrame(isGold ? id_gold : id);
    // cancelAnimationFrame(id);
    texture_promise.then(function(texture) {
      scene.background = texture; 
      camera.fov = VFOV;
      camera.updateProjectionMatrix();
      // move_to(image_id);
      log_pose();
      move_to(image_id, cylinder_frame, world_frame, false, isGold)
    });
  });
  rotate_tween.chain(zoom_tween);
  if(isGold) {
    animate_gold();
  } else {
    if (!playing) {
      animate();
    }
  }
  rotate_tween.start();
}

function take_action_demo(image_id, cylinder_frame, camera, camera_pose, renderer, scene, world_frame, isGold) {
  var texture_promise = matt.loadCubeTexture(cube_urls(scan, image_id)); // start fetching textures
  var target = cylinder_frame.getObjectByName(image_id);

  // Camera up vector
  var camera_up = new THREE.Vector3(0,1,0);
  var camera_look = new THREE.Vector3(0,0,-1);
  var camera_m = get_camera_pose(camera, camera_pose);
  var zero = new THREE.Vector3(0,0,0);
  camera_m.setPosition(zero);
  camera_up.applyMatrix4(camera_m);
  camera_up.normalize();
  camera_look.applyMatrix4(camera_m);
  camera_look.normalize();

  // look direction
  var look = target.position.clone();
  look.sub(camera_pose.position);
  look.projectOnPlane(camera_up);
  look.normalize();
  // Simplified - assumes z is zero
  var rotate = Math.atan2(look.y,look.x) - Math.atan2(camera_look.y,camera_look.x);
  if (rotate < -Math.PI) rotate += 2*Math.PI;
  if (rotate > Math.PI) rotate -= 2*Math.PI;

  var target_y = camera.rotation.y + rotate;
  var rotate_tween = new TWEEN.Tween({
    x: camera.rotation.x,
    y: camera.rotation.y,
    z: camera.rotation.z})
  .to( {
    x: camera.rotation.x,
    y: target_y,
    z: 0 }, 2000*Math.abs(rotate) )
  .easing( TWEEN.Easing.Cubic.InOut)
  .onUpdate(function() {
    camera.rotation.x = this.x;
    camera.rotation.y = this.y;
    camera.rotation.z = this.z;

    // camera.updateProjectionMatrix();

    render(renderer, scene, camera);
  });
  var new_vfov = VFOV*0.95;
  var zoom_tween = new TWEEN.Tween({
    vfov: VFOV})
  .to( {vfov: new_vfov }, 500 )
  .easing(TWEEN.Easing.Cubic.InOut)
  .onUpdate(function() {
    camera.fov = this.vfov;
    camera.updateProjectionMatrix();
    render(renderer, scene, camera);
  })
  .onComplete(function(){
    cancelAnimationFrame(isGold ? id_gold : id);
    // cancelAnimationFrame(id);
    texture_promise.then(function(texture) {
      scene.background = texture;
      camera.fov = VFOV;
      camera.updateProjectionMatrix();
      // move_to(image_id);
      move_to_demo(image_id, false)
    });
  });
  rotate_tween.chain(zoom_tween);
  animate();
  rotate_tween.start();
}

// Display the Scene
function render(renderer, scene, camera) {
  renderer.render(scene, camera);
}

// tweening
function animate() {
  id = requestAnimationFrame( animate );
  TWEEN.update();
}

function animate_gold() {
  id_gold = requestAnimationFrame( animate_gold );
  TWEEN.update();
}


// Gold path animation
window.play_animation = function() {
  if (!playing){
    window.reset_gold();
    var cylinders = cylinder_frame_gold.children;
    for (var i = 0; i < cylinders.length; ++i){
      cylinders[i].visible = false;
    }

    if (!reversed_policies[curr_image_id_gold]) {
      reversed_policies[curr_image_id_gold] = true;
      var idx;
      var shortest_len = -1;
      shortest_policy = -1;
      for (idx=0; idx < optimal_policies.length; idx++) {
        if (optimal_policies[idx][curr_image_id_gold]) {
          var idx_len = optimal_policies[idx][curr_image_id_gold].length;
          if (shortest_policy == -1 || idx_len < shortest_len) {
            shortest_policy = optimal_policies[idx];
            shortest_len = idx_len;
          }
        }
      }
      shortest_policy[curr_image_id_gold].reverse();
    }

    path = shortest_policy[curr_image_id_gold];
    // path.shift(); // remove the first node because we're already there
    document.getElementById("user_gold_play").disabled = true;
    step = 0;
    playing = true;
    step_forward();
  }
};

window.reset_gold = function() {
  if (!path) return;
  step = 0;
  playing = false;

  cancelAnimationFrame(id);

  gold_skybox_reinit();
  reinitialize_data(scan, curr_image_id);
  curr_image_id_gold = curr_image_id;

  camera_pose_gold.rotation.x = camera_pose.rotation.x;
  camera_pose_gold.rotation.y = camera_pose.rotation.y;
  camera_pose_gold.rotation.z = camera_pose.rotation.z;
  camera_pose_gold.rotation.order = camera_pose.rotation.order;

  camera_gold.fov = VFOV;
  camera_gold.rotation.x = camera.rotation.x;
  camera_gold.rotation.y = camera.rotation.y;
  camera_gold.rotation.z = camera.rotation.z;
  camera_gold.rotation.order = camera.rotation.order;
  render(renderer_gold, scene_gold, camera_gold);
  document.getElementById("user_gold_play").disabled = false;

};

function step_forward(){
  if (step >= window.MAX_GOLD_LENGTH || step >= path.length-1) {
    playing = false;
    step = 0;

    setTimeout(function() {
      gold_skybox_reinit();
      reinitialize_data(scan, path[0]);

      camera_pose_gold.rotation.x = camera_pose.rotation.x;
      camera_pose_gold.rotation.y = camera_pose.rotation.y;
      camera_pose_gold.rotation.z = camera_pose.rotation.z;
      camera_pose_gold.rotation.order = camera_pose.rotation.order;

      camera_gold.rotation.x = camera.rotation.x;
      camera_gold.rotation.y = camera.rotation.y;
      camera_gold.rotation.z = camera.rotation.z;
      camera_gold.rotation.order = camera.rotation.order;

      render(renderer_gold, scene_gold, camera_gold);

      document.getElementById("user_gold_play").disabled = false;
    }, 3000);
  } else {
    step += 1;
    window.update_oracle_camera({img_id: path[step]}, true);
  }
};

try {
  var context = new AudioContext();
} catch(e) {}

window.playSound = function(frequency, type){
  try {
    var o = context.createOscillator();
    var g = context.createGain();
    o.type = type;
    o.connect(g);
    o.frequency.value = frequency;
    g.connect(context.destination);
    o.start(0);

    g.gain.exponentialRampToValueAtTime(
        0.00001, context.currentTime + 1
    )
  }catch(e) {}
};


