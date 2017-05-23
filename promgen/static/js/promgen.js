/*
# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
*/
$( document ).ready(function() {
  $.ajax({url: "/ajax/alert",}).done(function( data ) {
    for (var key in data) {
      console.log("Replacing " + key)
      $(key).replaceWith(data[key])
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
