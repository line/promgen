$( document ).ready(function() {
  $.ajax({url: "/ajax/alert",}).done(function( data ) {
    for (var key in data) {
      console.log("Writing " + key)
      $("#" + key).html(data[key]).show()
  }
  });
});
