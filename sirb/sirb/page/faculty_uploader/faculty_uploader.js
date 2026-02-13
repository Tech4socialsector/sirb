frappe.pages['faculty-uploader'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Upload Faculty List',
        single_column: true
    });

    // Content container
    const container = $(`
        <div class="upload-intro" style="max-width: 600px; margin: 40px auto 20px;">
            <p>Select an Academic Organizational Unit and upload a CSV file.</p>
        </div>
        <div style="display: flex; flex-direction: column; align-items: center; gap: 20px;">
            <button class="btn btn-primary btn-lg">Upload File</button>
            
            <div class="progress d-none" style="width: 400px; height: 20px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 0%"></div>
            </div>
			<div class="task-log d-none" style="
				width: 100%; 
				max-width: 500px; 
				height: 150px; 
				overflow-y: auto; 
				background: #f8f9fa; 
				border: 1px solid #d1d8dd; 
				border-radius: 4px; 
				padding: 10px; 
				font-family: monospace; 
				font-size: 12px;
			"></div>
        </div>
    `).appendTo(page.body);
    
    const button = container.find('button');

    const progress_container = container.find('.progress');
	const task_log = container.find('.task-log');

    button.on('click', () => {
        open_upload_dialog(progress_container, task_log, button);
    });
};

function open_upload_dialog(progress_container, task_log, button) {
	task_log.empty();
    frappe.realtime.off("sirb_faculty_import_progress");

    // Clear UI state
    task_log.empty().addClass('d-none');
    progress_container.addClass('d-none');
    progress_container.find('.progress-bar').css('width', '0%').text('0%');        
    // 1. Listen for realtime events
    frappe.realtime.on("sirb_faculty_import_progress", (data) => {
        const percentage = data.progress || 0;         
        console.log(data)
        progress_container.find('.progress-bar').css('width', percentage + '%').text(Math.round(percentage) + '%');
		task_log.removeClass('d-none');
        // Update the status text
		if (data.status) {
			// Add timestamp for a professional look
			const timestamp = frappe.datetime.now_time();
			if ('error' in data) {
				task_log.append(`
					<div style="color:red;margin-bottom: 2px; border-bottom: 1px solid #eee; padding-bottom: 2px;">
						<span class="text-muted" style="margin-right: 8px;">[${timestamp}]</span>
						<span>${data.status}</span>
					</div>
				`);
			} else {
				task_log.append(`
					<div style="margin-bottom: 2px; border-bottom: 1px solid #eee; padding-bottom: 2px;">
						<span class="text-muted" style="margin-right: 8px;">[${timestamp}]</span>
						<span>${data.status}</span>
					</div>
				`);
			}

			
			// Auto-scroll to bottom
			task_log.scrollTop(task_log[0].scrollHeight);
		}

        if (percentage >= 100) {
            frappe.show_alert({message: __('Upload Complete'), indicator: 'green'});
			task_log.append(`<div style="color: green; font-weight: bold; margin-top: 5px;">${__('Upload Completed.')}</div>`);
			task_log.scrollTop(task_log[0].scrollHeight);			
            setTimeout(() => {
                progress_container.addClass('d-none');
            }, 2000);
            frappe.realtime.off("sirb_faculty_import_progress");
        }
    }); 

    const dialog = new frappe.ui.Dialog({
        title: 'Upload Faculty List',
        fields: [
            { fieldtype: 'Link', label: 'Select Academic Organizational Unit', fieldname: 'ao_unit', options: 'Academic Organizational Unit', reqd: 1 },
            { fieldtype: 'Attach', label: 'Upload File', fieldname: 'file', reqd: 1 }
        ],
        primary_action_label: 'Submit',
        primary_action(values) {
            // Reset and Show progress
            progress_container.removeClass('d-none');
            progress_container.find('.progress-bar').css('width', '0%');
            button.prop('disabled', true);
            
            dialog.hide(); // Hide dialog so user sees the progress bar on the page

            frappe.call({
                method: 'sirb.api.enque_faculty_upload',
                args: {
                    ao_unit: values.ao_unit,
                    file_url: values.file
                },
                callback: function(r) {
                    if (r.message) frappe.show_alert({message: r.message, indicator: 'blue'});
                },
                always() {
                    button.prop('disabled', false);
                }               
            });
        }
    });
    dialog.show();
};
