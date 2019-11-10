/*
# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
*/

function update_page(data) {
  for (var key in data) {
    console.log("Replacing %s", key);
    var ele = $(data[key]);
    $(key).replaceWith(ele);
  }
}

$(document).ready(function() {
  $('[data-toggle="popover"]').popover();
  $('[data-toggle="tooltip"]').tooltip();

  $('[data-source]').click(function() {
    var btn = $(this);
    var query = btn.data('source') === 'self' ? btn.text() : $(btn.data('source')).val();

    $(btn.data('target')).html('Loading...').show();
    btn.data('query', query);
    console.log("Testing Query: %s", query);
    $.post(btn.data('href'), btn.data()).done(update_page);
  }).css('cursor', 'pointer');

  $('[data-copyto]').click(function(){
    var ele = $(this);
    $(ele.data('copyto')).val(ele.text())
  }).css('cursor', 'pointer');

  $('[data-filter]').change(function(){
    var search = this.value.toUpperCase();
    $(this.dataset.filter).each(function(i, ele){
      var txt = $(this).text().toUpperCase();
      ele.style.display = txt.indexOf(search) > -1 ? "" : "none"
    })
  });
});
