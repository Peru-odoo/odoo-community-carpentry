/** @odoo-module **/

const { Component, useState, onWillStart } = owl;
import { useService } from "@web/core/utils/hooks";

// Launch item (<li> element)
export class PlanningLeftSidePanel_LaunchItem extends Component {
    setup () {
        super.setup();
        
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({is_done: this.props.launch.is_done});
    }
    
    toggleLaunch () {
        this.state.is_done = !this.state.is_done;
        this.orm.write("carpentry.group.launch", [this.props.launch.id], {is_done: this.state.is_done});
    }
    openLaunch() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'carpentry.group.launch',
            res_id: this.props.launch.id,
            views: [[false, 'form']],
            name: this.props.launch.name,
            target: 'new',
            context: {'carpentry_planning': true}
        });
    }
}
PlanningLeftSidePanel_LaunchItem.template = "carpentry_planning.PlanningLeftSidePanel_LaunchItem";
PlanningLeftSidePanel_LaunchItem.props = {
    launch: Object,
    isSelected: Boolean,
    selectLaunch: Function
};


// List (left side pannel)
export class PlanningLeftSidePanel extends Component {
    setup () {
        this.state = useState({selectedLaunchId: this.props.model.launchId});
    }
    
    // Pre-Select 1st opened launch
    get launchIds() {
        return this.props.model.data.launchIds;
    }
    // Filtering by launch
    selectLaunch(launch) {
        if (launch) {
            this.props.model.setLaunch(launch); // model
            this.state.selectedLaunchId = launch.id; // reload left side panel
        }
    }

    // Simili-pager (prev, next)
    get goLeft() {
        return this.launchIds.length > 1 && this.state.selectedLaunchId != this.launchIds[0].id
    }
    get goRight() {
        const lastIndex = this.launchIds.length - 1
        return this.launchIds.length > 1 && this.state.selectedLaunchId != this.launchIds[lastIndex].id
    }
    move (direction) {
        const currentIndex = this.launchIds.findIndex((launch) => launch.id == this.state.selectedLaunchId);
        if (currentIndex + direction >= 0 && currentIndex + direction < this.launchIds.length) {
            this.selectLaunch(this.launchIds[currentIndex + direction]);
        }
    }
}
PlanningLeftSidePanel.template = "carpentry_planning.PlanningLeftSidePanel";
PlanningLeftSidePanel.components = { PlanningLeftSidePanel_LaunchItem };
PlanningLeftSidePanel.props = {
    model: true
};
