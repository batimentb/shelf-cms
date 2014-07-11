var AdminModelActions = function(actionErrorMessage, actionConfirmations) {
    // Actions helpers. TODO: Move to separate file
    this.execute = function(name) {
        var selected = $('input.action-checkbox:checked').size();

        if (selected === 0) {
            alert(actionErrorMessage);
            return false;
        }

        var msg = actionConfirmations[name];

        if (!!msg)
            if (!confirm(msg))
                return false;

        // Update hidden form and submit it
        var form = $('#action_form');
        $('#action', form).val(name);

        $('input.action-checkbox', form).remove();
        $('input.action-checkbox:checked').each(function() {
            form.append($(this).clone());
        });

        form.submit();

        return false;
    };

    $(function() {
        $('.select-all a').click(function(e) {
            $('.select-all').hide();
            $('.select-none').show();
            $('.model-list thead input.action-rowtoggle').prop('checked', true);
            $('#select-all').val("1");
        });

        $('.select-none a').click(function(e) {
            $('.select-none').hide();
            $('.select-all').show();
            $('.select-all a').hide();
            $('.select-all span').html('0');
            $('.model-list thead input.action-rowtoggle').prop('checked', false);
            $('.model-list tbody tr input.action-checkbox:checked').prop('checked', false);
            $('.model-list tbody tr.selected').removeClass('selected');
            $('#select-all').val("0");
            $('#select-page').val("0");
        });

        $('.action-rowtoggle').change(function() {
            if ($(this).prop("checked") == true)
            {
                $('.model-list tbody tr').addClass('selected');
                $('.model-list tbody input.action-checkbox').prop("checked", true);
                $('.select-all a').show();
                $('#select-page').val("1");
            }
            else
            {
                $('.model-list tbody tr').removeClass('selected');
                $('.model-list tbody input.action-checkbox').prop("checked", false);
                $('.select-all a').hide();
                $('.select-none').hide();
                $('.select-all').show();
                $('#select-all').val("0");
                $('#select-page').val("0");
            }

            $('.select-all span').html($('.model-list tbody tr.selected').length);
            if ($('.model-list tbody tr.selected').length > 0)
                $("li.actions.delete").removeClass('disabled');
            else
                $("li.actions.delete").addClass('disabled');
        });

        $('input.action-checkbox').change(function() {
            if (this.checked)
               $(this).closest('tr').addClass('selected');
            else
               $(this).closest('tr').removeClass('selected');
        });

        $('.model-list tbody tr').click(function (e) {
            /* state switch when row is clicked */
            if ($(this).hasClass('selected'))
            {
                $(this).removeClass('selected');
                $(this).find('input.action-checkbox').prop("checked", false);
            }
            else
            {
                $(this).addClass('selected');
                $(this).find('input.action-checkbox').prop("checked", true);
            }

            /* changing count value */
            $('.select-all span').html($('.model-list tbody tr.selected').length);

            /* switching back to select all mode */
            $('.select-none').hide();
            $('.select-all').show();
            $('#select-all').val("0");

            /* if all is selected check head input */
            if ($('.model-list tbody tr.selected').length == $('.model-list tbody tr').length)
            {
                $('.model-list thead input.action-rowtoggle').prop('checked', true);
                $('.select-all a').show();
                $('#select-page').val("1");
            }
            else
            {
                $('.model-list thead input.action-rowtoggle').prop('checked', false);
                $('.select-all a').hide();
                $('#select-page').val("0");
            }

            if ($('.model-list tbody tr.selected').length > 0)
                $("li.actions.delete").removeClass('disabled');
            else
                $("li.actions.delete").addClass('disabled');
        });

        /* Set selected class on already checked row */
        $('.model-list tbody tr input.action-checkbox:checked').each(
            function (i, elem) {
                $(elem).closest('tr').addClass('selected');
            }
        );

        /* If all is selected; display select-all */
        if ($('.model-list tbody tr.selected').length == $('.model-list tbody tr').length)
        {
            $('.select-all a').show();
        }
        else
        {
            $('.select-all a').hide();
        }

        if ($('#select-all').val() == "1")
        {
            $('.select-all').hide();
            $('.select-none').show();
        }

        $('.select-all span').html($('.model-list tbody tr.selected').length);
    });
};
