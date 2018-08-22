
// For hover-over tooltip
$(document).ready(function(){
  $('[data-toggle="tooltip"]').tooltip();
});

// For JS ajax requests using POST
// https://stackoverflow.com/a/22929593/2320823
var csrftoken = $('meta[name=csrf-token]').attr('content');

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    }
});


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
