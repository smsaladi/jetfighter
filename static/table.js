$(document).ready(function() {
  var table = $('#jfTable').DataTable( {
    columns: [
        { name: 'expand'},
        { name: 'title', "width": "65%" },
        { name: 'date', "width": "15%" },
        { name: 'link'},
        { name: 'status' },
        { name: 'authors' },
    ],
    'columnDefs' : [
      { 'orderable': false, 'targets': [0] }
      ],
      "pageLength": 50,
      dom: 'lrtp',
      "lengthChange": false,
      "fnInitComplete" : function( oSettings, json ){
        $('#pagebox').val(oSettings['_iDisplayLength']);
      }
  });


  // Add event listener for opening and closing details
  $('table').on('click', 'td.details-control', function () {
    var tr = $(this).closest('tr');
    var row = table.row( tr );
    if ( row.child.isShown() ) {
      row.child.hide();
      tr.removeClass('shown');
    }
    else {
      if (!row.child()) {
        prev = retrieve_previews( row.data().DT_RowId, false);
        row.child(prev);
      }
      row.child.show();
      tr.addClass('shown');
    }
  });

  $("#filterbox").keyup(function() {
    table.search(this.value).draw();
  });

  $('#pagebox').on("change", function () {
    table.page.len(this.value).draw();
  });

});
