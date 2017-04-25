/*
# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
*/
$( document ).ready(function() {
  $.ajax({url: "/ajax/alert",}).done(function( data ) {
    for (var key in data) {
      if (key == '#alert-all') {
        console.log('Replacing button')
        div = $(data[key])
        btn = $(data[key]).find('div.panel-heading a')
        header = div.find('div.panel-heading')
        table = div.find('table')

        // Replace our loading button with the alert-all button
        btn.addClass('navbar-btn')
        $('#alert-load').replaceWith(btn)

        // Replace the header button with just the header text
        header.text(header.text())

        // Move properties from our <table> to our base <div>
        div.attr('id', table.attr('id'))
        div.addClass('collapse')

        // Clear up our attributes on the table
        table.removeAttr('id')
        table.removeClass('collapse')

        console.log("Replacing " + key)
        $(key).replaceWith(div)
      } else {
        console.log("Replacing " + key)
        $(key).replaceWith(data[key])
      }
  }
  });

  $('#test_clause').click(function(){
    var btn = $(this)
    var query = $(btn.data('source')).val()

    $(btn.data('target')).html('<p>Loading...</p>')
    console.log("Testing Query: " + query)
    $.post("/ajax/clause", {'query': query, 'shard': btn.data('shard-id')}).done(function(result){
      for (var key in result) {
        console.log("Replacing " + key)
        $(key).replaceWith(result[key])
      }
    })
  })

});
