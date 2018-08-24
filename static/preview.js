// Initiate conversion of images.
// Separate call for which pages and retrieving images
function retrieve_previews(id, all_pages = false) {
  info = $('#infotemplate').clone();
  info.removeAttr('id');
  p_preview = info.find(".paperpreview");

  detail_link = info.find(".detail_link");
  detail_link.attr("href", '/detail/' + id);

  function insertPages(pgs) {
    Object.keys(pgs).map(function(pg, index) {
      status = pgs[pg];
      pvt = $('#pgpreviewtempl').clone();
      pvt.removeAttr('id');

      // add link to page in pdf
      a_link = pvt.find("a");
      a_link.attr("href",
        'http://biorxiv.org/cgi/content/short/' + id + '.pdf#page=' + pg
      );

      // call to retrieve page and insert it
      p_preview.append(pvt);

      if (status == "true")
        pvt.find("a").children().addClass("preview-detected");
      else
        pvt.find("a").children().addClass("preview-notdetected");

      // Retrieve image numbers along with per-page parse statuses
      // remove placeholders
      i = pvt.find("img");
      i.hide();
      i.attr("src", "");
      $.ajax({
        url : "/preview/" + id + "/" + pg,
        dataType: 'json',
      }).done((function( pvt, i ){
        return function(data) {
          pvt.find(".placeholder").remove();
          i.attr("src", data);
          i.show();
        };
      })( pvt, i ));

    });
  }

  // get page numbers to show and initiate callback
  if (all_pages)
    url = "/pages/" + id + "?all=1";
  else
    url = "/pages/" + id;

  $.ajax({
    url : url,
    dataType: 'json'
  }).done(insertPages);

  return info;
}
