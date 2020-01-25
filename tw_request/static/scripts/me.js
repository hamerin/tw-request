$(document).ready(function () {
  function ajax_retrieve(callback) {
    $.ajax({
      url: '/me_ajax',
      dataType: 'json',
      type: 'GET',
      success: function (result) {
        $('#main').html(result['html']);
        callback();
      }
    });
  }

  function ajax_post() {
    $.ajax({
      url: '/me_ajax',
      dataType: 'json',
      type: 'POST',
      data: $('#form > form').serializeObject(),
      success: function (result) {
        $('#main').html(result['html']);
        $('#form > form')[0].reset();

        $('#submit_button').click(function () {
          ajax_post();
        });
    
        $('#search_button').click(function () {
          window.location.replace("/user/" + $("#search_id").val())
        });
      }
    })
  }

  ajax_retrieve(() => {
    $('#submit_button').click(function () {
      ajax_post();
    });

    $('#search_button').click(function () {
      window.location.replace("/user/" + $("#search_id").val())
    });

    $('#search_id').keyup(function (e) {
      e.preventDefault();
      if(e.keyCode == 13) {
        window.location.replace("/user/" + $("#search_id").val())
      }
    });
  });
});