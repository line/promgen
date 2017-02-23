$( document ).ready(function() {
  $.ajax({url: "/ajax/alert",}).done(function( data ) {
    for (var key in data) {
      console.log("Writing " + key)
      if (key == 'alert-all') {
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

        $('#alert-all').replaceWith(div)
      } else {
        $("#" + key).replaceWith(data[key])
      }
  }
  });
});
