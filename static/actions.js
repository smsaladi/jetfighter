function send_action(button, action) {
  // Disable button to avoid multiple clicks
  button.attr('disabled','disabled');

  id = button.closest('tr').attr('id');
  var status = $("<div>", {"class": "fa fa-circle-notch fa-spin"});
      button.closest('td').append(status);

  function replacePlaceholder(data) {
    status.removeClass("fa fa-circle-notch fa-spin");
    status.addClass("status-text");
    status.html(data['message']);
  }

  $.ajax({
      type: "POST",
      url :  "/" + action + "/" + id,
      dataType: 'json',
    }).done(replacePlaceholder);
}

function toggle_status() {
  send_action($(this), 'toggle');
}

function send_email() {
  send_action($(this), 'notify');
}

$(document).ready(function(){
  // suggested here: https://datatables.net/forums/discussion/36627
  $("#jfTable tbody").on('click', 'tr td .btn-email',
    send_email
  );
  $("#jfTable tbody").on('click', 'tr td .btn-fix',
    toggle_status
  );
});