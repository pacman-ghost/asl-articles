import React from "react" ;
import Dialog from "@material-ui/core/Dialog" ;
import DialogTitle from "@material-ui/core/DialogTitle" ;
import DialogContent from "@material-ui/core/DialogContent" ;
import DialogActions from "@material-ui/core/DialogActions" ;
import Button from "@material-ui/core/Button" ;
import "./ModalForm.css" ;
import { slugify } from "./utils" ;

// --------------------------------------------------------------------

export default class ModalForm extends React.Component
{

    render() {
        let buttons = [] ;
        for ( let btn in this.props.buttons ) {
            buttons.push(
                <Button key={btn} color="primary" className={slugify(btn)}
                  onClick = { this.props.buttons[btn] }
                > {btn} </Button>
            ) ;
        }
        return ( <Dialog id={this.props.formId} className="modal-form" open={true} onClose={this.onClose.bind(this)} disableBackdropClick>
            <DialogTitle style={{background:this.props.titleColor}}> {this.props.title} </DialogTitle>
            <DialogContent dividers> {this.props.content} </DialogContent>
            <DialogActions> {buttons} </DialogActions>
        </Dialog> ) ;
    }

    onClose() {
        // close the dialog
        if ( this.props.buttons.Cancel )
            this.props.buttons.Cancel() ;
    }

}
