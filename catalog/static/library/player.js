var audio = undefined;

if (typeof django != 'undefined') {
    (function($) {
        "use strict";
        $(function() {

          $('a.play').click(function(e){
            e.preventDefault();
            var $url = $(this).data('url');
            $('#source_wav').attr('src', $url);
            var $audio = $('#player');
            $audio[0].pause();
            $audio[0].load(); //suspends and restores all audio element
            $audio[0].oncanplaythrough = $audio[0].play();
          });

        });
    })(django.jQuery);
}
