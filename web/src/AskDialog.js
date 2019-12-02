import React from "react" ;
import Dialog from "@material-ui/core/Dialog" ;
import DialogContent from "@material-ui/core/DialogContent" ;
import DialogActions from "@material-ui/core/DialogActions" ;
import Button from "@material-ui/core/Button" ;
import "./AskDialog.css" ;
import { slugify } from "./utils" ;

// --------------------------------------------------------------------

export default class AskDialog extends React.Component
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
        return ( <Dialog id="ask" open={true} onClose={this.onClose.bind(this)} disableBackdropClick>
            <DialogContent> {this.props.content} </DialogContent>
            <DialogActions> {buttons} </DialogActions>
        </Dialog> ) ;
    }

    onClose() {
        // figure out which button to auto-click
        const keys = Object.keys( this.props.buttons ) ;
        let notify = (keys.length === 1) ? this.props.buttons[ keys[0] ] : this.props.buttons.Cancel ;
        if ( notify )
            notify() ;
    }

}
