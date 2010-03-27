(function() {
    var $ = window.$ || window.jQuery;
    $(document).ready(function() {
        var EXAMPLE_DATA = '{\n  "FIELD":"some-value"\n}\n';
        
        $('.form-row.code').each(function(i, nRow) {
            var nCode = $($('textarea', nRow)[0])
            var nCodeId = nCode.attr('id');
            
            var isInline = ($(nCode).parents('.inline-group').length != 0);
            
            var nData = $('<textarea>').attr({rows:10, cols:45}).val(EXAMPLE_DATA);
            var nResults = $('<textarea>').attr({rows:10, cols:45, readOnly:true}).val('');
            var nContainer = $('<div>').css('display', 'none');
            var nLabel = $('<label>')
                .text('Execute Code')
                .addClass('exec_label')
                .click(function(e) {
                    nContainer.slideToggle();
                });

            $(nRow).append(
                $('<div>').append(
                    nLabel,
                    nContainer.append(
                        $('<span>').addClass('exec_data_label').text('Field Data'),
                        $('<br>'),
                        nData,
                        $('<button>').text('Execute').click(function(e) {
                            e.preventDefault();
                            nResults.val('');
                            try {
                                var json_data = $.parseJSON(nData.val()); 
                            } catch(e) {
                                alert("Couldn't parse data");
                                return;
                            }
                            $.getJSON(
                                '/data_dict/tag/eval/', 
                                {
                                    'fields':nData.val(), 
                                    'code':nCode.val()
                                }, 
                                function(data, textStatus) {
                                    if (data.status == 'ok') {
                                        nResults.css({borderColor:'green'}).val(data.value);
                                    } else {
                                        nResults.css({borderColor:'red'}).val(data.error);
                                    }
                            })
                        }),
                        $('<span>&rarr;</span>'),
                        nResults
                    )
                )
            );
        });
    });
})();