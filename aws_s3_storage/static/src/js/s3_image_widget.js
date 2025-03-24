/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {Component, useRef} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class S3ImagePreviewWidget extends Component {
    static template = "aws_s3_storage.S3ImagePreviewWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.url = this.props.value || false;
        this.containerRef = useRef("container");
        this.dialogService = useService("dialog");
    }

    openPreview() {
        if (!this.url) return;

        const {url} = this;

        this.dialogService.add("S3ImagePreviewDialog", {
            title: _t("S3 Image Preview"),
            size: "xl",
            contentClass: "p-0",
            bodyClass: "p-0",
            renderFooter: () => {
                return [
                    {
                        text: _t("Open in New Tab"),
                        classes: "btn-primary",
                        click: () => window.open(url, '_blank'),
                    },
                    {
                        text: _t("Close"),
                        close: true,
                    }
                ];
            },
            render: () => {
                const content = document.createElement('div');
                content.className = 's3-image-modal-content';

                const iframe = document.createElement('iframe');
                iframe.src = url;
                iframe.className = 's3-image-iframe';
                iframe.style.width = '100%';
                iframe.style.height = 'calc(80vh - 120px)';
                iframe.style.border = 'none';
                iframe.frameBorder = '0';
                iframe.allowFullscreen = true;

                content.appendChild(iframe);
                return content;
            }
        });
    }
}

S3ImagePreviewWidget.supportedTypes = ["char"];

registry.category("fields").add("s3_image_preview", S3ImagePreviewWidget);