// Initiate conversion of images.
// Separate call for which pages and retrieving images
function retrieve_previews(id, all_pages = false) {
  info = $('#infotemplate').clone()[0];
  info.removeAttribute('id');
  p_preview = $(info).find(".paperpreview")[0];

  detail_link = $(info).find(".detail_link");
  detail_link.attr("href", '/detail/' + id);

  // Retrieve image numbers along with per-page parse statuses
  // add placeholders on the page until finally retrieved
  function insertPage(id, pg, i) {
      i.src = '';
      i.className += " fa fa-circle-o-notch fa-spin";
      function replacePagePlaceholder(data) {
        i.src = data;
        i.classList.remove('fa');
        i.classList.remove('fa-circle-o-notch');
        i.classList.remove('fa-spin');
      }
      $.ajax({
        url : "/preview/" + id + "/" + pg,
        dataType: 'json',
      }).done(replacePagePlaceholder);
  }

  function insertPages(pgs) {
    Object.keys(pgs).map(function(pg, index) {
      status = pgs[pg];
      pvt = $('#pgpreviewtempl').clone()[0];
      pvt.removeAttribute('id');

      // add link to page in pdf
      a_link = $(pvt).find("a");
      a_link.attr("href",
        'http://biorxiv.org/cgi/content/short/' + id + '.pdf#page=' + pg
      );

      // call to retrieve page and insert it
      p_preview.appendChild(pvt);
      i = $(pvt).find("img")[0];

      if (status == "true") {
        i.classList.add("img-preview-detected");
      } else {
        i.classList.add("img-preview-notdetected");
      }
      insertPage(id, pg, i);
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
