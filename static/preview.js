// Initiate conversion of images.
// Separate call for which pages and retrieving images
function retrieve_previews(id, all_pages = false) {
  info = $('#infotemplate').clone().removeAttr('id');
  p_preview = info.find(".paperpreview");

  // add link to details page
  info.find(".detail_link").attr("href", '/detail/' + id);

  function insertPages(data) {
    pdf_url = data['pdf_url'];
    $.each(data['pages'], function(pg, status) {

      pvt = $('#pgpreviewtempl').clone().removeAttr('id');

      // add link to page in pdf
      pvt.find("a").attr("href", pdf_url + '#page=' + pg);

      // call to retrieve page and insert it
      p_preview.append(pvt);

      if (status == true)
        pvt.find("a").children().addClass("preview-detected");
      else
        pvt.find("a").children().addClass("preview-notdetected");

      // Retrieve image numbers along with per-page parse statuses
      // remove placeholders
      pvt
        .find("img")
        .hide()
        .attr("src", "/iiif/" + id + "/page/" + pg + "/full/250,/0/default.jpg")
        .on("load", function() {
          $(this).show().parent().find(".placeholder").remove();
        });
    });
  }

  // get page numbers to show and initiate callback
  url = "/pages/" + id;
  if (all_pages)
    url += "?all=1";

  $.ajax({
    url : url,
    dataType: 'json'
  }).done(insertPages);

  return info;
}
