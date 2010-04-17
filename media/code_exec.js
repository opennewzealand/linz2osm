(function() {
    var $ = window.$ || window.jQuery;
    $(document).ready(function() {
        var EXAMPLE_DATA = '{\n  "FIELD":"some-value"\n}\n';
        
        $('.form-row.code').each(function(i, nRow) {
            var nCode = $($('textarea', nRow)[0])
            var nCodeId = nCode.attr('id');
            
            var isInline = ($(nCode).parents('.inline-group').length != 0);
            
            var nData = $('<textarea>').addClass('vLargeTextField').val($.cookie('linz2osm_execdata') || EXAMPLE_DATA);
            var nResults = $('<textarea>').addClass('vLargeTextField').attr({readOnly:true}).val('');
            var nContainer = $('<div>').css('display', 'none');
            var nLabel = $('<label>')
                .text('Test Code')
                .addClass('exec_label')
                .click(function(e) {
                    nContainer.slideToggle();
                });

            $(nRow).append(
                $('<div>').addClass('codeExec').append(
                    nLabel,
                    nContainer.append(
                        $('<span>').addClass('exec_data_label').text('Field Data'),
                        $('<br>'),
                        nData,
                        $('<button>').html('Run &rarr;').click(function(e) {
                            e.preventDefault();
                            nResults.val('');
                            try {
                                var json_data = $.parseJSON(nData.val()); 
                            } catch(e) {
                                alert("Couldn't parse data");
                                return;
                            }
                            $.ajax({
                                url: '/data_dict/tag/eval/',
                                dataType: 'json',
                                data: {
                                    'fields':nData.val(), 
                                    'code':nCode.val()
                                },
                                success: function(data, textStatus) {
                                    $.cookie('linz2osm_execdata', nData.val(), {path:'/data_dict/'});
                                    if (data.status == 'ok') {
                                        nResults.css({borderColor:'green'}).val(data.value);
                                    } else {
                                        nResults.css({borderColor:'red'}).val(data.error);
                                    }
                                },
                                error: function(xhr, textStatus, e) {
                                    console.log("EVAL XHR Error:", xhr, textStatus, e);
                                    nResults.css({borderColor:'red'}).val("Server Error: " + textStatus);
                                }
                            });
                        }),
                        nResults
                    )
                )
            );
        });
    });
})();