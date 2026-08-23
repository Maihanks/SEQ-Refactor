package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass4Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass4 subject = new LeafClass4();
        assertEquals("two", subject.leafSwitch(2));
    }

}
