odoo.define('hrm.hide_button_edit', function (require) {
    "use strict";
    console.log("hide_button_edit");
    document.addEventListener("DOMContentLoaded", function() {
        var body = document.body;

        body.addEventListener("click", function() {
            // Code xử lý sự kiện khi một ô được click
            console.log("click");
            var state_draft = document.querySelectorAll("button.o_arrow_button");
            var button_edit = document.querySelectorAll("button.o_form_button_edit");
            console.log(state_draft);
            console.log(button_edit);
            state_draft.forEach(function(state){
                if(state.textContent.includes("Nháp") && state.getAttribute("title") != "Not active state"){
                    button_edit[0].hidden = false;
                }else{
                    button_edit[0].hidden = true;
                }
            });
        });
    });
});