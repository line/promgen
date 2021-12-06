/*
 * Copyright (c) 2021 LINE Corporation
 * These sources are released under the terms of the MIT license: see LICENSE
 */

function groupByLabel(items, label) {
  const groups = new Map();

  for (const item of items) {
    const key = item.labels[label];
    if (!key) {
      continue;
    }

    const group = groups.get(key);
    if (group) {
      group.push(item);
    } else {
      groups.set(key, [item]);
    }
  }

  return groups;
}

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

  $('[data-toggle="toggle"]').bootstrapSwitch();
  $('[data-toggle="toggle"][data-action]').on('switchChange.bootstrapSwitch', function(event, state) {
    if (window.confirm("Are you sure?")) {
      $.post(this.dataset.action, this.dataset).done(function(data){
        // Ideally we would directly update things that need to be updated
        // but a page redraw is a bit easier since that also allows us to
        // update our page messages
        window.location = data.redirect
      });
    } else {
      // If we click the cancel button, then we restore the old state and
      // use the third parameter to skip re-firing the change event
      $(this).bootstrapSwitch('state', !state, true);
    }
  });

  $('[data-filter]').change(function(){
    var search = this.value.toUpperCase();
    $(this.dataset.filter).each(function(i, ele){
      var txt = $(this).text().toUpperCase();
      ele.style.display = txt.indexOf(search) > -1 ? "" : "none"
    })
  });
});
