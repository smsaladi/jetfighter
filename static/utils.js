
// unused
// remove rows without results
function removeNotYetRun() {
  $('.notyetrun').remove();
  this.disabled=true;
}
// remove rows with negative results
function removeNotDetected() {
  $('.notdetected').remove();
  this.disabled=true;
}

// For hover-over tooltip
$(document).ready(function(){
    $('[data-toggle="tooltip"]').tooltip();
});
