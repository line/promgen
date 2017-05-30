/*
# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
*/

function mute_tag() {
  var labels = $.parseJSON(this.dataset.labels);
  var form = $('#mute-form')
  for (var label in labels) {
    var value = labels[label]
    console.log('Adding %s %s', label, value)

    form.find('a.' + label).remove()

    input = $('<input type="hidden" class="form-control" />')
    input.val(value).attr('name', 'label.' + label)

    span = $('<a class="label label-warning"></a>').addClass(label)
    span.attr('onclick', 'this.parentNode.removeChild(this); return false;')
    span.text(label + ':' + value)
    span.append(input)
    span.append($('<span class="glyphicon glyphicon-remove" aria-hidden="true"></span>'))

    form.find('div.labels').append(span)
  }

  form.show();
}

function update_page(data) {
  for (var key in data) {
    console.log("Replacing %s", key)
    var ele = $(data[key])
    ele.find("a[data-labels]").click(mute_tag);
    $(key).replaceWith(ele)
  }
}

$(document).ready(function() {
  $("a[data-labels]").click(mute_tag)
  $.ajax("/ajax/alert").done(update_page);
  $.ajax("/ajax/mute").done(update_page);

  $('#test_clause').click(function() {
    var btn = $(this)
    var query = $(btn.data('source')).val()

    $(btn.data('target')).html('<p>Loading...</p>')
    console.log("Testing Query: %s", query)
    $.post("/ajax/clause", {
      'query': query,
      'shard': btn.data('shard-id')
    }).done(update_page);
  })
});
