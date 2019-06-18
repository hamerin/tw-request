jQuery.fn.serializeObject = function() {
  var obj = null;
  try {
    if ( this[0].tagName && this[0].tagName.toUpperCase() == "FORM" ) {
      var arr = this.serializeArray();
      if ( arr ) {
        obj = {};
        jQuery.each(arr, function() {
          obj[this.name] = this.value;
        });				
      }//if ( arr ) {
 		}
  }
  catch(e) {alert(e.message);}
  finally  {}
  
  return obj;
};

$(document).ready(function () {
  $('#discard').click(function () {
    $('#isSharing').closest("div").children('label').removeClass("disabled");
    $('#isSharing').removeAttr("disabled");
    $('#isSharing').prop("checked", true);
  });
  
  $('#accept').click(function () {
    $('#isSharing').closest("div").children('label').addClass("disabled");
    $('#isSharing').attr("disabled", "");
    $('#isSharing').prop("checked", false);
  });

  function ajax_retrieve() {
    $.ajax({
      url: '/me_ajax',
      dataType: 'json',
      type: 'GET',
      success: function(result) {
        $("#request-get").remove();
        $("#request-complete").remove();
        $('#form').after(result['html']);
      }
    });
  }

  function ajax_post() {
    $.ajax({
      url: '/me_ajax',
      dataType: 'json',
      type: 'POST',
      data: $('#form > form').serializeObject(),
      success: function(result) {
        $("#request-get").remove();
        $("#request-complete").remove();
        $('#form').after(result['html']);
        $('#form > form')[0].reset();
      }
    })
  }

  ajax_retrieve();

  $('#submit_button').click(function () {
    ajax_post();
  });
});