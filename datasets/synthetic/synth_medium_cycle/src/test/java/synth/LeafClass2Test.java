package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass2Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass2 subject = new LeafClass2();
        assertEquals("two", subject.leafSwitch(2));
    }

}
